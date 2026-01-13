# settings.py

from typing import Any


class SettingsLoader:
    """
    Singleton для хранения конфигурации проекта.
    Реализован через __new__ для простоты и читаемости.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = {}
            cls._instance._load_defaults()
        return cls._instance

    def _load_defaults(self):
        self._settings = {
            "DATA_PATH": "data/",
            "USERS_FILE": "data/users.json",
            "PORTFOLIOS_FILE": "data/portfolios.json",
            "RATES_FILE": "data/rates.json",
            "RATES_TTL_SECONDS": 300,  # 5 минут
            "DEFAULT_BASE_CURRENCY": "USD",
            "LOG_LEVEL": "INFO",
            "LOG_PATH": "logs/actions.log",
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def reload(self):
        """
        Перезагрузка конфигурации.
        Пока просто пересоздаёт дефолтные значения.
        """
        self._load_defaults()