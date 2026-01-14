# models.py

import hashlib
from datetime import datetime

from .currencies import get_currency
from .exceptions import InsufficientFundsError


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime
    ):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value:
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256((password + self._salt).encode("utf-8")).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self._hash_password(password) == self._hashed_password

    def change_password(self, new_password: str):
        if not new_password:
            raise ValueError("Пароль обязателен")
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = self._hash_password(new_password)

    def get_user_info(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat()
        }


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        if not currency_code:
            raise ValueError("Код валюты не может быть пустым")
        self.currency_code = currency_code.upper()
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float):
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        self.balance += float(amount)

    def withdraw(self, amount: float):
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        if amount > self.balance:
            raise InsufficientFundsError(
                self.currency_code,
                self.balance,
                float(amount),
            )
        self.balance -= float(amount)

    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self.balance:.4f}"


class Portfolio:
    def __init__(self, user_id: int, wallets: dict[str, Wallet] | None = None):
        self._user_id = user_id
        self._wallets = wallets or {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict:
        return self._wallets.copy()

    def add_currency(self, currency_code: str):
        if not currency_code:
            raise ValueError("Код валюты не может быть пустым")
        currency_code = currency_code.upper()
        get_currency(currency_code)
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк '{currency_code}' уже существует")
        self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str):
        if not currency_code:
            return None
        return self._wallets.get(currency_code.upper())

    def get_total_value(self, base_currency: str = "USD", rate_provider=None) -> float:
        """
        Считает суммарную стоимость портфеля в base_currency.
        rate_provider: callable(from_code, to_code) -> float или dict с ключом "rate".
        """
        base_currency = (base_currency or "").upper()
        if not base_currency:
            raise ValueError("Код валюты не может быть пустым")
        get_currency(base_currency)

        total = 0.0
        for code, wallet in self._wallets.items():
            code = code.upper()
            if code == base_currency:
                total += wallet.balance
                continue
            if rate_provider is None:
                raise ValueError("Не передан rate_provider для конвертации валют")
            info = rate_provider(code, base_currency)
            rate = float(info["rate"]) if isinstance(info, dict) else float(info)
            total += wallet.balance * rate
        return total