# usecases.py

import hashlib
from datetime import datetime
from pathlib import Path

from .models import Portfolio, User, Wallet
from .utils import _load_json, _save_json

DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def _generate_user_id(users: list[dict]) -> int:
    if not users:
        return 1
    return max(user.get("user_id", 0) for user in users) + 1


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> User:
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if not password:
        raise ValueError("Пароль обязателен")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = _load_json(USERS_FILE, [])

    for user in users:
        if user.get("username") == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = _generate_user_id(users)
    salt = str(user_id)
    hashed_password = _hash_password(password, salt)
    registration_date = datetime.now()

    new_user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
        registration_date=registration_date
    )

    users.append({
        "user_id": user_id,
        "username": username,
        "hashed_password": hashed_password,
        "salt": salt,
        "registration_date": registration_date.isoformat()
    })
    _save_json(USERS_FILE, users)

    portfolios = _load_json(PORTFOLIOS_FILE, [])
    portfolios.append({
        "user_id": user_id,
        "wallets": {"USD": {"balance": 0.0}}
    })
    _save_json(PORTFOLIOS_FILE, portfolios)

    return new_user


def login_user(username: str, password: str) -> User:
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if not password:
        raise ValueError("Пароль обязателен")

    users = _load_json(USERS_FILE, [])

    for user_data in users:
        if user_data.get("username") == username:
            user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                hashed_password=user_data["hashed_password"],
                salt=user_data["salt"],
                registration_date=datetime.fromisoformat(
                    user_data["registration_date"]
                )
            )

            if not user.verify_password(password):
                raise ValueError("Неверный пароль")

            return user

    raise ValueError(f"Пользователь '{username}' не найден")


def load_rates() -> dict:
    return _load_json(RATES_FILE, {})


def get_rate(from_currency: str, to_currency: str) -> float:
    from_currency = (from_currency or "").upper()
    to_currency = (to_currency or "").upper()

    if not from_currency or not to_currency:
        raise ValueError("Код валюты не может быть пустым")

    if from_currency == to_currency:
        return 1.0

    rates = load_rates()

    key = f"{from_currency}_{to_currency}"
    reverse_key = f"{to_currency}_{from_currency}"

    # игнорируем 'source'/'last_refresh': курс — это dict с ключом 'rate'
    if key in rates and isinstance(rates[key], dict) and "rate" in rates[key]:
        return float(rates[key]["rate"])

    if (
        reverse_key in rates 
        and isinstance(rates[reverse_key], dict) 
        and "rate" in rates[reverse_key]
    ):
        return 1.0 / float(rates[reverse_key]["rate"])

    raise ValueError(f"Не удалось получить курс для {from_currency}→{to_currency}")


def load_portfolio(user_id: int) -> Portfolio:
    portfolios = _load_json(PORTFOLIOS_FILE, [])

    for p in portfolios:
        if p.get("user_id") == user_id:
            wallets = {}
            for code, data in (p.get("wallets") or {}).items():
                wallet = Wallet(code)
                wallet.balance = (data or {}).get("balance", 0.0)
                wallets[code] = wallet

            return Portfolio(user_id=user_id, wallets=wallets)

    raise ValueError("Портфель пользователя не найден")


def save_portfolio(portfolio: Portfolio):
    portfolios = _load_json(PORTFOLIOS_FILE, [])

    for p in portfolios:
        if p.get("user_id") == portfolio.user_id:
            p["wallets"] = {
                code: {"balance": wallet.balance}
                for code, wallet in portfolio.wallets.items()
            }
            _save_json(PORTFOLIOS_FILE, portfolios)
            return

    raise ValueError("Не удалось сохранить портфель")


def show_portfolio(user: User, base_currency: str = "USD") -> dict:
    base_currency = (base_currency or "").upper()
    if not base_currency:
        raise ValueError("Код валюты не может быть пустым")

    portfolio = load_portfolio(user.user_id)

    if not portfolio.wallets:
        return {"wallets": [], "total": 0.0, "base": base_currency}

    result = []
    total = 0.0

    for code, wallet in portfolio.wallets.items():
        rate = 1.0 if code == base_currency else get_rate(code, base_currency)
        value = wallet.balance * rate
        total += value

        result.append({
            "currency": code,
            "balance": wallet.balance,
            "value": value
        })

    return {
        "wallets": result,
        "total": total,
        "base": base_currency
    }


def _ensure_wallet(portfolio: Portfolio, currency: str) -> Wallet:
    currency = (currency or "").upper()
    if not currency:
        raise ValueError("Код валюты не может быть пустым")

    wallet = portfolio.get_wallet(currency)
    if wallet is None:
        portfolio.add_currency(currency)
        wallet = portfolio.get_wallet(currency)
    return wallet


def buy_currency(user: User, currency: str, amount: float):
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    if not currency:
        raise ValueError("Код валюты не может быть пустым")

    currency = currency.upper()
    portfolio = load_portfolio(user.user_id)

    usd_wallet = _ensure_wallet(portfolio, "USD")
    cur_wallet = _ensure_wallet(portfolio, currency)

    rate = get_rate(currency, "USD")
    cost_usd = amount * rate

    usd_wallet.withdraw(cost_usd)

    before = cur_wallet.balance
    cur_wallet.deposit(amount)

    save_portfolio(portfolio)

    return {
        "currency": currency,
        "amount": amount,
        "rate": rate,
        "cost_usd": cost_usd,
        "before": before,
        "after": cur_wallet.balance,
        "usd_after": usd_wallet.balance
    }


def sell_currency(user: User, currency: str, amount: float):
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    if not currency:
        raise ValueError("Код валюты не может быть пустым")

    currency = currency.upper()
    portfolio = load_portfolio(user.user_id)

    usd_wallet = _ensure_wallet(portfolio, "USD")

    cur_wallet = portfolio.get_wallet(currency)
    if cur_wallet is None:
        raise ValueError(f"У вас нет кошелька '{currency}'")

    rate = get_rate(currency, "USD")
    revenue_usd = amount * rate

    before = cur_wallet.balance
    cur_wallet.withdraw(amount)

    usd_wallet.deposit(revenue_usd)

    save_portfolio(portfolio)

    return {
        "currency": currency,
        "amount": amount,
        "rate": rate,
        "revenue_usd": revenue_usd,
        "before": before,
        "after": cur_wallet.balance,
        "usd_after": usd_wallet.balance
    }