# database.py

from pathlib import Path

from valutatrade_hub.core.utils import _load_json, _save_json
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Singleton для доступа к JSON-хранилищу.
    Реализован через __new__ для простоты и читаемости.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SettingsLoader()
        return cls._instance

    def load_users(self) -> list[dict]:
        path = Path(self._settings.get("USERS_FILE"))
        return _load_json(path, [])

    def save_users(self, users: list[dict]) -> None:
        path = Path(self._settings.get("USERS_FILE"))
        _save_json(path, users)

    def load_portfolios(self) -> list[dict]:
        path = Path(self._settings.get("PORTFOLIOS_FILE"))
        return _load_json(path, [])

    def save_portfolios(self, portfolios: list[dict]) -> None:
        path = Path(self._settings.get("PORTFOLIOS_FILE"))
        _save_json(path, portfolios)

    def load_rates(self) -> dict:
        path = Path(self._settings.get("RATES_FILE"))
        return _load_json(path, {})

    def save_rates(self, rates: dict) -> None:
        path = Path(self._settings.get("RATES_FILE"))
        _save_json(path, rates)