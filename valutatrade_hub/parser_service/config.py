# config.py

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParserConfig:
    # Ключ загружается из переменной окружения
    EXCHANGERATE_API_KEY: str | None = os.getenv("EXCHANGERATE_API_KEY")

    # Эндпоинты
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Параметры запросов
    BASE_FIAT_CURRENCY: str = "USD"
    REQUEST_TIMEOUT: int = 10

    # Списки валют
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    # Пути к файлам
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    def validate(self) -> None:
        if not isinstance(self.REQUEST_TIMEOUT, int) or self.REQUEST_TIMEOUT <= 0:
            raise ValueError("REQUEST_TIMEOUT must be positive int")
        if not isinstance(self.BASE_FIAT_CURRENCY, str) or not self.BASE_FIAT_CURRENCY:
            raise ValueError("BASE_FIAT_CURRENCY must be non-empty str")
        if not isinstance(self.RATES_FILE_PATH, str) or not self.RATES_FILE_PATH:
            raise ValueError("RATES_FILE_PATH must be non-empty str")
        if not isinstance(self.HISTORY_FILE_PATH, str) or not self.HISTORY_FILE_PATH:
            raise ValueError("HISTORY_FILE_PATH must be non-empty str")