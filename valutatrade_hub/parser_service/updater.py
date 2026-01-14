# updater.py

import logging
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class RatesUpdater:
    """
    Класс для обновления курсов валют через список API-клиентов
    Поддерживает обновление snapshot и сохранение истории
    """
    def __init__(self, config: ParserConfig, api_clients: list, storage_module):
        self._config = config
        self._clients = api_clients
        self._storage = storage_module
        self._logger = logging.getLogger(__name__)

    def _utc_now_z(self) -> str:
        dt = datetime.now(timezone.utc).replace(microsecond=0)
        return dt.isoformat().replace("+00:00", "Z")

    def run_update(self) -> dict:
        self._logger.info("RatesUpdater: start")

        combined: dict[str, float] = {}
        sources: dict[str, str] = {}
        updated_at_map: dict[str, str] = {}
        last_refresh = self._utc_now_z()

        for client in self._clients:
            client_name = client.__class__.__name__
            try:
                self._logger.info("RatesUpdater: fetch start client=%s", client_name)
                data = client.fetch_rates()
                if not isinstance(data, dict):
                    raise ApiRequestError(f"{client_name}: invalid rates format")

                combined.update(data)
                for pair_key in data.keys():
                    sources[pair_key] = client_name
                    if hasattr(client, "last_updated_at_map"):
                        ts = getattr(client, "last_updated_at_map", {}).get(pair_key)
                        if isinstance(ts, str) and ts:
                            updated_at_map[pair_key] = ts
                    if hasattr(client, "last_updated_at"):
                        ts = getattr(client, "last_updated_at", None)
                        if isinstance(ts, str) and ts:
                            updated_at_map[pair_key] = ts

                self._logger.info(
                    "RatesUpdater: fetch ok client=%s pairs=%s",
                    client_name,
                    len(data),
                )
            except ApiRequestError:
                self._logger.exception(
                    "RatesUpdater: fetch failed client=%s",
                    client_name,
                )
                continue
            except Exception:
                self._logger.exception(
                    "RatesUpdater: unexpected error client=%s",
                    client_name,
                )
                continue

        updated = 0
        history_appended = 0
        for pair_key, rate in combined.items():
            source = sources.get(pair_key, "Unknown")
            updated_at = updated_at_map.get(pair_key, last_refresh)
            try:
                # История измерений
                try:
                    from_cur, to_cur = pair_key.split("_", 1)
                    record = self._storage.make_rate_record(
                        from_cur, to_cur, rate, updated_at, source
                    )
                    ok_hist = self._storage.append_exchange_rate_record(
                        self._config.HISTORY_FILE_PATH, record
                    )
                    if ok_hist:
                        history_appended += 1
                except Exception:
                    self._logger.exception(
                        "RatesUpdater: history append failed pair=%s", pair_key
                    )

                # Snapshot
                ok = self._storage.upsert_pair_to_rates_json(
                    self._config.RATES_FILE_PATH,
                    pair_key,
                    rate,
                    updated_at,
                    source,
                )
                if ok:
                    updated += 1
            except Exception:
                self._logger.exception("RatesUpdater: store failed pair=%s", pair_key)

        self._logger.info(
            "RatesUpdater: done total_pairs=%s updated=%s history_appended=%s "
            "last_refresh=%s",
            len(combined),
            updated,
            history_appended,
            last_refresh,
        )

        return {
            "total_pairs": len(combined),
            "updated_pairs": updated,
            "last_refresh": last_refresh,
        }