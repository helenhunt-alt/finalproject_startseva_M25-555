# interface.py

import shlex

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
    show_portfolio,
)
from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater

current_user = None


def _build_updater(source: str | None) -> RatesUpdater:
    config = ParserConfig()
    config.validate()

    source_norm = (source or "").strip().lower()

    clients = []
    if not source_norm:
        clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]
    elif source_norm in ("coingecko", "cg"):
        clients = [CoinGeckoClient(config)]
    elif source_norm in ("exchangerate", "exchange", "exchangerate-api", "er"):
        clients = [ExchangeRateApiClient(config)]
    else:
        raise ValueError(
            "Неизвестный источник. Используйте --source coingecko или "
            "--source exchangerate"
        )

    return RatesUpdater(config=config, api_clients=clients, storage_module=storage)


def _normalize_source_name(s: str) -> str:
    s = (s or "").strip()
    low = s.lower()
    if low in ("coingecko", "coingeckoclient"):
        return "CoinGecko"
    if low in ("exchangerate", "exchangerate-api", "exchangerateapiclient"):
        return "ExchangeRate-API"
    return s or "Unknown"


def _format_rate(v: float) -> str:
    if abs(v) >= 100:
        return f"{v:.2f}"
    if abs(v) >= 1:
        return f"{v:.6f}".rstrip("0").rstrip(".")
    return f"{v:.8f}".rstrip("0").rstrip(".")


def cmd_register(args):
    """
    Регистрирует нового пользователя
    Аргументы через словарь args: --username, --password
    Выводит результат регистрации или ошибку
    """
    username = args.get("--username")
    password = args.get("--password")
    if not username or not password:
        print("Ошибка: необходимо указать --username и --password")
        return

    try:
        user = register_user(username, password)
        print(
            f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
            f"Войдите: login --username {user.username} --password ****"
        )
    except ValueError as e:
        print(f"Ошибка: {e}")


def cmd_login(args):
    """
    Логин пользователя
    Аргументы через словарь args: --username, --password
    Устанавливает current_user при успешном входе
    """
    global current_user
    username = args.get("--username")
    password = args.get("--password")
    if not username or not password:
        print("Ошибка: необходимо указать --username и --password")
        return

    try:
        current_user = login_user(username, password)
        print(f"Вы вошли как '{current_user.username}'")
    except ValueError as e:
        print(f"Ошибка: {e}")


def cmd_show_portfolio(args):
    """
    Показывает портфель текущего пользователя в указанной базе валют
    Аргументы через словарь args: --base (по умолчанию USD)
    """
    if not current_user:
        print("Сначала выполните login")
        return

    base = (args.get("--base", "USD") or "USD").upper()
    try:
        data = show_portfolio(current_user, base)
    except CurrencyNotFoundError as e:
        print(f"Ошибка: {e}")
        print(
            "Подсказка: используйте get-rate --from USD --to BTC или проверьте список "
            "поддерживаемых кодов."
        )
        return
    except ApiRequestError as e:
        print(f"Ошибка: {e}")
        print("Подсказка: повторите позже или проверьте сеть.")
        return
    except ValueError as e:
        print(f"Ошибка: {e}")
        return

    print(f"Портфель пользователя '{current_user.username}' (база: {base}):")
    if not data["wallets"]:
        print("Кошельков пока нет")
        return

    for w in data["wallets"]:
        print(f"- {w['currency']}: {w['balance']:.4f} → {w['value']:.2f} {base}")
    print("---------------------------------")
    print(f"ИТОГО: {data['total']:.2f} {base}")


def cmd_buy(args):
    """
    Покупка валюты для текущего пользователя
    Аргументы через словарь args: --currency, --amount
    """
    if not current_user:
        print("Сначала выполните login")
        return
    try:
        currency = args["--currency"]
        amount = float(args["--amount"])
        res = buy_currency(current_user, currency, amount)
        print(
            f"Покупка выполнена: {res['amount']:.4f} {res['currency']} "
            f"по курсу {res['rate']:.2f} USD/{res['currency']}"
        )
        print("Изменения в портфеле:")
        print(
            f"- {res['currency']}: было {res['before']:.4f} → "
            f"стало {res['after']:.4f}"
        )
        print(f"- USD: стало {res['usd_after']:.4f}")
        print(f"Оценочная стоимость покупки: {res['cost_usd']:.2f} USD")
    except InsufficientFundsError as e:
        print(f"Ошибка: {e}")
        print("Подсказка: пополните USD-кошелёк и повторите покупку.")
    except CurrencyNotFoundError as e:
        print(f"Ошибка: {e}")
        print(
            "Подсказка: проверьте код валюты и используйте get-rate для "
            "проверки курсов."
        )
    except ApiRequestError as e:
        print(f"Ошибка: {e}")
        print(
            "Подсказка: курс недоступен (кеш просрочен и обновление не удалось). "
            "Повторите позже."
        )
    except ValueError as e:
        print(f"Ошибка: {e}")
    except KeyError:
        print("Ошибка: необходимо указать --currency и --amount")


def cmd_sell(args):
    """
    Продажа валюты для текущего пользователя
    Аргументы через словарь args: --currency, --amount
    """
    if not current_user:
        print("Сначала выполните login")
        return
    try:
        currency = args["--currency"]
        amount = float(args["--amount"])
        res = sell_currency(current_user, currency, amount)
        print(
            f"Продажа выполнена: {res['amount']:.4f} {res['currency']} "
            f"по курсу {res['rate']:.2f} USD/{res['currency']}"
        )
        print("Изменения в портфеле:")
        print(
            f"- {res['currency']}: было {res['before']:.4f} → "
            f"стало {res['after']:.4f}"
        )
        print(f"- USD: стало {res['usd_after']:.4f}")
        print(f"Оценочная выручка: {res['revenue_usd']:.2f} USD")
    except InsufficientFundsError as e:
        print(f"Ошибка: {e}")
    except CurrencyNotFoundError as e:
        print(f"Ошибка: {e}")
        print(
            "Подсказка: проверьте код валюты и используйте get-rate для "
            "проверки курсов."
        )
    except ApiRequestError as e:
        print(f"Ошибка: {e}")
        print(
            "Подсказка: курс недоступен (кеш просрочен и обновление не удалось). "
            "Повторите позже."
        )
    except ValueError as e:
        print(f"Ошибка: {e}")
    except KeyError:
        print("Ошибка: необходимо указать --currency и --amount")


def cmd_get_rate(args):
    """
    Получает курс одной валюты к другой из кеша или API
    Аргументы через словарь args: --from, --to
    """
    try:
        info = get_rate(args["--from"], args["--to"])
        src = args["--from"].upper()
        dst = args["--to"].upper()
        print(
            f"Курс {src}→{dst}: "
            f"{info['rate']} (обновлено: {info['updated_at']})"
        )
    except CurrencyNotFoundError as e:
        print(f"Ошибка: {e}")
        print(
            "Подсказка: проверьте код (USD/EUR/BTC/ETH) или используйте get-rate "
            "--from USD --to BTC."
        )
    except ApiRequestError as e:
        print(f"Ошибка: {e}")
        print("Подсказка: курс сейчас недоступен. Повторите позже.")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except KeyError:
        print("Ошибка: необходимо указать --from и --to")


def cmd_update_rates(args):
    """
    Обновляет локальный кеш курсов валют
    Аргументы через словарь args: --source (coingecko или exchangerate)
    """
    source = args.get("--source")
    print("INFO: Starting rates update...")

    try:
        updater = _build_updater(source)
    except ValueError as e:
        print(f"Ошибка: {e}")
        return

    try:
        summary = updater.run_update()
    except ApiRequestError as e:
        print(f"ERROR: {e}")
        return
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return

    updated = summary.get("updated_pairs", 0)
    last_refresh = summary.get("last_refresh")

    print(
        "Update successful. Total rates updated: "
        f"{updated}. Last refresh: {last_refresh}"
    )


def cmd_show_rates(args):
    """
    Показывает курсы валют из локального кеша.
    Аргументы через словарь args:
        --currency: фильтр по валюте
        --base: базовая валюта
        --top: ограничить количество выводимых пар
    """
    currency = (args.get("--currency") or "").strip().upper()
    base = (args.get("--base") or "").strip().upper()
    top_raw = args.get("--top")

    try:
        top = int(top_raw) if top_raw is not None else None
        if top is not None and top <= 0:
            raise ValueError
    except ValueError:
        print("Ошибка: --top должен быть положительным числом")
        return

    config = ParserConfig()
    config.validate()

    snapshot = storage.load_rates_snapshot(config.RATES_FILE_PATH)
    pairs = snapshot.get("pairs") or {}
    last_refresh = snapshot.get("last_refresh")

    if not pairs:
        print(
            "Локальный кеш курсов пуст. Выполните 'update-rates', "
            "чтобы загрузить данные."
        )
        return

    rows: list[tuple[str, float, str]] = []
    for pair_key, rec in pairs.items():
        if not isinstance(rec, dict) or "rate" not in rec:
            continue

        try:
            from_cur, to_cur = pair_key.split("_", 1)
        except ValueError:
            continue

        rate = rec.get("rate")
        updated_at = rec.get("updated_at")

        if not isinstance(rate, (int, float)):
            continue

        from_cur = str(from_cur).upper()
        to_cur = str(to_cur).upper()

        if currency:
            if currency not in (from_cur, to_cur):
                continue

        if base:
            if to_cur == base:
                rows.append((pair_key, float(rate), str(updated_at or "")))
                continue

            rev_key = f"{base}_{from_cur}"
            rev = pairs.get(rev_key)
            if isinstance(rev, dict) and isinstance(rev.get("rate"), (int, float)):
                rev_rate = float(rev["rate"])
                if rev_rate > 0:
                    inv = 1.0 / rev_rate
                    rows.append(
                        (
                            f"{from_cur}_{base}",
                            inv,
                            str(rev.get("updated_at") or ""),
                        )
                    )
            continue

        rows.append((pair_key, float(rate), str(updated_at or "")))

    if not rows:
        if currency:
            print(f"Курс для '{currency}' не найден в кеше.")
        else:
            print("Нет данных по заданным фильтрам.")
        return

    if top is not None:
        rows.sort(key=lambda x: x[1], reverse=True)
        rows = rows[:top]
    else:
        rows.sort(key=lambda x: x[0])

    print(f"Rates from cache (updated at {last_refresh}):")
    for pair_key, rate, updated_at in rows:
        print(f"- {pair_key}: {_format_rate(rate)}")


COMMANDS = {
    "register": cmd_register,
    "login": cmd_login,
    "show-portfolio": cmd_show_portfolio,
    "buy": cmd_buy,
    "sell": cmd_sell,
    "get-rate": cmd_get_rate,
    "update-rates": cmd_update_rates,
    "show-rates": cmd_show_rates,
}


def parse_args(tokens):
    """
    Парсит аргументы командной строки
    argv: список аргументов (по умолчанию sys.argv[1:])
    Возвращает Namespace с полями для каждой команды и её параметров
    """
    args = {}
    it = iter(tokens)
    for t in it:
        if t.startswith("--"):
            try:
                args[t] = next(it)
            except StopIteration:
                raise ValueError(f"У аргумента {t} отсутствует значение")
    return args


def run():
    """
    Главный цикл CLI
    Разбирает команду и вызывает соответствующую функцию-обработчик
    """
    while True:
        raw = input("> ")
        tokens = shlex.split(raw)
        if not tokens:
            continue

        cmd = tokens[0]
        if cmd == "exit":
            break

        handler = COMMANDS.get(cmd)
        if not handler:
            print("Неизвестная команда")
            continue

        try:
            args = parse_args(tokens[1:])
            handler(args)
        except ValueError as e:
            print(f"Ошибка: {e}")