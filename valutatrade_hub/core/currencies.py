# currencies.py

from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError, CurrencyValidationError


class Currency(ABC):
    def __init__(self, name: str, code: str):
        self._validate_name(name)
        self._validate_code(code)

        self.name = name
        self.code = code

    @staticmethod
    def _validate_name(name: str):
        if not isinstance(name, str) or not name.strip():
            raise CurrencyValidationError("Название валюты не может быть пустым")

    @staticmethod
    def _validate_code(code: str):
        if (
            not isinstance(code, str)
            or not code.isupper()
            or not (2 <= len(code) <= 5)
            or " " in code
        ):
            raise CurrencyValidationError(
                "Код валюты должен быть в верхнем регистре и содержать 2–5 символов "
                "без пробелов"
            )

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление валюты для UI и логов."""
        pass


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)

        if not issuing_country or not isinstance(issuing_country, str):
            raise CurrencyValidationError("Страна эмиссии должна быть непустой строкой")

        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)

        if not algorithm or not isinstance(algorithm, str):
            raise CurrencyValidationError("Алгоритм должен быть непустой строкой")

        if not isinstance(market_cap, (int, float)) or market_cap < 0:
            raise CurrencyValidationError(
                "Капитализация должна быть неотрицательным числом"
            )

        self.algorithm = algorithm
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


_CURRENCY_REGISTRY = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
}

def get_currency(code: str) -> Currency:
    if not isinstance(code, str):
        raise CurrencyValidationError("Код валюты должен быть строкой")

    code = code.upper()

    try:
        return _CURRENCY_REGISTRY[code]
    except KeyError:
        raise CurrencyNotFoundError(code)