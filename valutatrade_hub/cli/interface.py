# interface.py

import shlex

from valutatrade_hub.core.usecases import (
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
    show_portfolio,
)

current_user = None


def cmd_register(args):
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
    if not current_user:
        print("Сначала выполните login")
        return

    base = (args.get("--base", "USD") or "USD").upper()
    try:
        data = show_portfolio(current_user, base)
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
        print(f"Оценочная стоимость покупки: {res['cost_usd']:.2f} USD")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except KeyError:
        print("Ошибка: необходимо указать --currency и --amount")


def cmd_sell(args):
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
        print(f"Оценочная выручка: {res['revenue_usd']:.2f} USD")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except KeyError:
        print("Ошибка: необходимо указать --currency и --amount")


def cmd_get_rate(args):
    try:
        rate = get_rate(args["--from"], args["--to"])
        print(f"Курс {args['--from'].upper()}→{args['--to'].upper()}: {rate}")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except KeyError:
        print("Ошибка: необходимо указать --from и --to")


COMMANDS = {
    "register": cmd_register,
    "login": cmd_login,
    "show-portfolio": cmd_show_portfolio,
    "buy": cmd_buy,
    "sell": cmd_sell,
    "get-rate": cmd_get_rate,
}


def parse_args(tokens):
    args = {}
    it = iter(tokens)
    for t in it:
        if t.startswith("--"):
            args[t] = next(it)
    return args


def run():
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

        args = parse_args(tokens[1:])
        handler(args)