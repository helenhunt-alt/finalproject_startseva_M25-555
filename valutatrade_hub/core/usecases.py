# usecases.py

import hashlib
from datetime import datetime

from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

from .currencies import get_currency
from .exceptions import ApiRequestError
from .models import Portfolio, User, Wallet

_settings = SettingsLoader()
_db = DatabaseManager()

RATES_TTL_SECONDS = int(_settings.get("RATES_TTL_SECONDS", 300))


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

    users = _db.load_users()

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
    _db.save_users(users)

    portfolios = _db.load_portfolios()
    portfolios.append({
        "user_id": user_id,
        "wallets": {"USD": {"balance": 0.0}}
    })
    _db.save_portfolios(portfolios)

    return new_user


def login_user(username: str, password: str) -> User:
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if not password:
        raise ValueError("Пароль обязателен")

    users = _db.load_users()

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
    return _db.load_rates()


def _is_rate_fresh(updated_at: str) -> bool:
    try:
        dt = datetime.fromisoformat(updated_at)
    except Exception:
        return False
    age = (datetime.now() - dt).total_seconds()
    return age <= RATES_TTL_SECONDS


def _refresh_rates_stub(rates: dict) -> dict:
    """
    Заглушка обновления курсов
    Реальный Parser Service отсутствует
    Курсы не обновляются, только фиксируется попытка refresh
    """
    if not isinstance(rates, dict):
        rates = {}
    rates["last_refresh"] = datetime.now().isoformat(timespec="seconds")
    rates["source"] = "Stub"
    return rates


def get_rate(from_currency: str, to_currency: str) -> dict:
    from_currency = (from_currency or "").upper()
    to_currency = (to_currency or "").upper()

    if not from_currency or not to_currency:
        raise ValueError("Код валюты не может быть пустым")

    get_currency(from_currency)
    get_currency(to_currency)

    if from_currency == to_currency:
        return {
            "rate": 1.0,
            "updated_at": datetime.now().isoformat(timespec="seconds")
        }

    rates = load_rates()

    key = f"{from_currency}_{to_currency}"
    reverse_key = f"{to_currency}_{from_currency}"

    rec = rates.get(key)
    if isinstance(rec, dict) and "rate" in rec:
        updated_at = rec.get("updated_at")
        if updated_at and _is_rate_fresh(updated_at):
            return {"rate": float(rec["rate"]), "updated_at": updated_at}

    rec_rev = rates.get(reverse_key)
    if isinstance(rec_rev, dict) and "rate" in rec_rev:
        updated_at = rec_rev.get("updated_at")
        if updated_at and _is_rate_fresh(updated_at):
            return {
                "rate": 1.0 / float(rec_rev["rate"]),
                "updated_at": updated_at
            }

    rates = _refresh_rates_stub(rates)
    _db.save_rates(rates)

    rec = rates.get(key)
    if (
        isinstance(rec, dict)
        and "rate" in rec
        and rec.get("updated_at")
        and _is_rate_fresh(rec["updated_at"])
    ):
        return {"rate": float(rec["rate"]), "updated_at": rec["updated_at"]}

    rec_rev = rates.get(reverse_key)
    if (
        isinstance(rec_rev, dict)
        and "rate" in rec_rev
        and rec_rev.get("updated_at")
        and _is_rate_fresh(rec_rev["updated_at"])
    ):
        return {
            "rate": 1.0 / float(rec_rev["rate"]),
            "updated_at": rec_rev["updated_at"]
        }

    raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен")


def load_portfolio(user_id: int) -> Portfolio:
    portfolios = _db.load_portfolios()

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
    portfolios = _db.load_portfolios()

    for p in portfolios:
        if p.get("user_id") == portfolio.user_id:
            p["wallets"] = {
                code: {"balance": wallet.balance}
                for code, wallet in portfolio.wallets.items()
            }
            _db.save_portfolios(portfolios)
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
        if code == base_currency:
            rate = 1.0
        else:
            rate = float(get_rate(code, base_currency)["rate"])
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


@log_action("BUY", verbose=True)
def buy_currency(user: User, currency: str, amount: float):
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    if not currency:
        raise ValueError("Код валюты не может быть пустым")

    currency = currency.upper()
    get_currency(currency)

    portfolio = load_portfolio(user.user_id)

    usd_wallet = _ensure_wallet(portfolio, "USD")
    cur_wallet = _ensure_wallet(portfolio, currency)

    rate_info = get_rate(currency, "USD")
    rate = float(rate_info["rate"])
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


@log_action("SELL", verbose=True)
def sell_currency(user: User, currency: str, amount: float):
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    if not currency:
        raise ValueError("Код валюты не может быть пустым")

    currency = currency.upper()
    get_currency(currency)
    
    portfolio = load_portfolio(user.user_id)

    usd_wallet = _ensure_wallet(portfolio, "USD")

    cur_wallet = portfolio.get_wallet(currency)
    if cur_wallet is None:
        raise ValueError(f"У вас нет кошелька '{currency}'")

    rate_info = get_rate(currency, "USD")
    rate = float(rate_info["rate"])
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