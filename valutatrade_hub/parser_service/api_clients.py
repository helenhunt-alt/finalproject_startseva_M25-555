# api_clients.py

from abc import ABC, abstractmethod
from datetime import datetime, timezone

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    @abstractmethod
    def fetch_rates(self) -> dict:
        """
        Возвращает курсы в стандартизированном формате:
        {"BTC_USD": 59337.21, "EUR_USD": 1.0786, ...}
        """
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self._config = config
        self.last_updated_at_map: dict[str, str] = {}

    @staticmethod
    def _unix_to_iso_z(ts: int | float) -> str:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).replace(microsecond=0)
        return dt.isoformat().replace("+00:00", "Z")

    def fetch_rates(self) -> dict:
        self.last_updated_at_map = {}
        vs = self._config.BASE_FIAT_CURRENCY.lower()

        ids = []
        for code in self._config.CRYPTO_CURRENCIES:
            code = str(code).upper()
            cg_id = self._config.CRYPTO_ID_MAP.get(code)
            if cg_id:
                ids.append(cg_id)

        if not ids:
            return {}

        params = {
            "ids": ",".join(ids),
            "vs_currencies": vs,
            "include_last_updated_at": "true",
        }

        try:
            response = requests.get(
                self._config.COINGECKO_URL,
                params=params,
                timeout=self._config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(
                f"Ошибка при обращении к внешнему API: CoinGecko ({e})"
            )

        if response.status_code != 200:
            raise ApiRequestError(
                f"Ошибка при обращении к внешнему API: CoinGecko HTTP "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except Exception as e:
            raise ApiRequestError(
                f"Ошибка при обращении к внешнему API: CoinGecko invalid JSON ({e})"
            )

        if not isinstance(data, dict):
            raise ApiRequestError(
                "Ошибка при обращении к внешнему API: CoinGecko unexpected response "
                "format"
            )

        result = {}
        base = self._config.BASE_FIAT_CURRENCY.upper()

        reverse_map = {}
        for code, cg_id in self._config.CRYPTO_ID_MAP.items():
            reverse_map[cg_id] = code

        for coin_id, payload in data.items():
            code = reverse_map.get(coin_id)
            if not code:
                continue
            if not isinstance(payload, dict):
                continue

            price = payload.get(vs)
            if isinstance(price, (int, float)) and float(price) > 0:
                pair_key = f"{code}_{base}"
                result[pair_key] = float(price)

                updated_unix = payload.get("last_updated_at")
                if isinstance(updated_unix, (int, float)):
                    self.last_updated_at_map[pair_key] = self._unix_to_iso_z(
                        updated_unix
                    )

        return result


class ExchangeRateApiClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self._config = config
        self.last_updated_at: str | None = None

    @staticmethod
    def _parse_time_last_update_utc(s: str) -> str:
        dt = (
            datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z")
            .astimezone(timezone.utc)
            .replace(microsecond=0)
        )
        return dt.isoformat().replace("+00:00", "Z")

    def fetch_rates(self) -> dict:
        self.last_updated_at = None
        if not self._config.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                "Ошибка при обращении к внешнему API: ExchangeRate-API "
                "(missing EXCHANGERATE_API_KEY)"
            )

        base = self._config.BASE_FIAT_CURRENCY.upper()
        url = (
            f"{self._config.EXCHANGERATE_API_URL}/"
            f"{self._config.EXCHANGERATE_API_KEY}/latest/{base}"
        )

        try:
            response = requests.get(url, timeout=self._config.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(
                f"Ошибка при обращении к внешнему API: ExchangeRate-API ({e})"
            )

        if response.status_code != 200:
            raise ApiRequestError(
                f"Ошибка при обращении к внешнему API: ExchangeRate-API HTTP "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except Exception as e:
            raise ApiRequestError(
                f"Ошибка при обращении к внешнему API: "
                f"ExchangeRate-API invalid JSON ({e})"
            )

        if not isinstance(data, dict):
            raise ApiRequestError(
                "Ошибка при обращении к внешнему API: "
                "ExchangeRate-API unexpected response format"
            )

        rates = data.get("rates")
        if rates is None:
            rates = data.get("conversion_rates")

        if not isinstance(rates, dict):
            raise ApiRequestError(
                "Ошибка при обращении к внешнему API: ExchangeRate-API missing rates"
            )

        tlu = data.get("time_last_update_utc")
        if isinstance(tlu, str) and tlu:
            try:
                self.last_updated_at = self._parse_time_last_update_utc(tlu)
            except Exception:
                self.last_updated_at = None

        result = {}

        for cur in self._config.FIAT_CURRENCIES:
            cur = str(cur).upper()
            v = rates.get(cur)
            if isinstance(v, (int, float)) and float(v) > 0:
                result[f"{cur}_{base}"] = 1.0 / float(v)

        return result