# storage.py

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def _validate_currency_code(code: str) -> str:
    if not isinstance(code, str):
        raise ValueError("currency code must be str")
    code = code.strip().upper()
    if not (2 <= len(code) <= 5):
        raise ValueError("currency code length must be 2..5")
    if " " in code:
        raise ValueError("currency code must not contain spaces")
    return code


def _validate_rate(rate) -> float:
    if not isinstance(rate, (int, float)):
        raise ValueError("rate must be number")
    rate = float(rate)
    if rate <= 0:
        raise ValueError("rate must be > 0")
    return rate


def _atomic_write_json(path: Path, data) -> None:
    """
    Атомарно сохраняет JSON в файл
    Сначала пишет во временный файл, затем заменяет оригинал
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _validate_timestamp_utc_z(timestamp: str) -> str:
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("timestamp must be non-empty str")
    if not timestamp.endswith("Z"):
        raise ValueError("timestamp must be ISO-UTC with 'Z' suffix")
    return timestamp


def make_rate_record(
    from_currency: str,
    to_currency: str,
    rate,
    timestamp: str,
    source: str,
    meta: dict | None = None,
) -> dict:
    from_code = _validate_currency_code(from_currency)
    to_code = _validate_currency_code(to_currency)
    ts = _validate_timestamp_utc_z(timestamp)
    r = _validate_rate(rate)

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be non-empty str")

    record_id = f"{from_code}_{to_code}_{ts}"

    if meta is not None and not isinstance(meta, dict):
        raise ValueError("meta must be dict or None")

    return {
        "id": record_id,
        "from_currency": from_code,
        "to_currency": to_code,
        "rate": r,
        "timestamp": ts,
        "source": source.strip(),
        "meta": meta or {},
    }


def load_exchange_rates(path: str | Path) -> list[dict]:
    """
    Загружает список исторических курсов из JSON
    Возвращает пустой список, если файла нет
    """
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("exchange_rates.json must contain a JSON list of records")
    return data


def append_exchange_rate_record(path: str | Path, record: dict) -> bool:
    """
    Добавляет новую запись курса в историю
    Если запись с таким ID уже есть — возвращает False
    """
    path = Path(path)
    if not isinstance(record, dict):
        raise ValueError("record must be dict")
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record must contain non-empty 'id'")

    records = load_exchange_rates(path)

    for r in records:
        if isinstance(r, dict) and r.get("id") == record_id:
            return False

    records.append(record)
    _atomic_write_json(path, records)
    return True


def _validate_pair_key(pair_key: str) -> str:
    if not isinstance(pair_key, str) or "_" not in pair_key:
        raise ValueError("pair key must look like FROM_TO")
    from_code, to_code = pair_key.split("_", 1)
    from_code = _validate_currency_code(from_code)
    to_code = _validate_currency_code(to_code)
    return f"{from_code}_{to_code}"


def _parse_iso_utc(s: str) -> datetime:
    if not isinstance(s, str) or not s:
        raise ValueError("updated_at must be non-empty str")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def utc_now_z() -> str:
    dt = datetime.now(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def load_rates_snapshot(path: str | Path) -> dict:
    """
    Загружает snapshot актуальных курсов из JSON
    Возвращает словарь {"pairs": {...}, "last_refresh": str|None}
    """
    path = Path(path)
    if not path.exists():
        return {"pairs": {}, "last_refresh": None}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("rates.json must contain a JSON object")

    pairs = data.get("pairs", {})
    if not isinstance(pairs, dict):
        raise ValueError("rates.json: 'pairs' must be an object")

    return {"pairs": pairs, "last_refresh": data.get("last_refresh")}


def is_pair_fresh(updated_at: str) -> bool:
    settings = SettingsLoader()
    ttl = int(settings.get("RATES_TTL_SECONDS", 300))

    dt = _parse_iso_utc(updated_at)
    age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
    return age <= ttl


def upsert_pair_to_rates_json(
    rates_json_path: str | Path,
    pair_key: str,
    rate,
    updated_at: str,
    source: str,
) -> bool:
    """
    Обновляет или добавляет пару валют в snapshot JSON
    Сохраняет только, если пришедший updated_at новее текущего
    """
    rates_json_path = Path(rates_json_path)
    pair_key = _validate_pair_key(pair_key)
    rate = _validate_rate(rate)

    if not isinstance(updated_at, str) or not updated_at:
        raise ValueError("updated_at must be non-empty str")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be non-empty str")

    incoming_dt = _parse_iso_utc(updated_at)

    snapshot = load_rates_snapshot(rates_json_path)
    pairs = snapshot["pairs"]

    current = pairs.get(pair_key)
    if isinstance(current, dict) and current.get("updated_at"):
        try:
            current_dt = _parse_iso_utc(current["updated_at"])
            if incoming_dt <= current_dt:
                return False
        except Exception:
            pass

    pairs[pair_key] = {
        "rate": rate,
        "updated_at": updated_at,
        "source": source.strip(),
    }

    out = {
        "pairs": pairs,
        "last_refresh": utc_now_z(),
    }
    _atomic_write_json(rates_json_path, out)
    return True