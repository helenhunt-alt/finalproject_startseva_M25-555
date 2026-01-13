# Final Project - Валютный кошелек

CLI-приложение для симуляции торговли валютами с локальным хранением данных.

Проект реализует Core Service платформы ValutaTrade Hub и позволяет пользователям
регистрироваться, управлять валютным портфелем, покупать и продавать валюты по текущим курсам.

---

## Функциональность

- регистрация и аутентификация пользователей;
- хранение пользователей и портфелей в JSON;
- управление кошельками валют;
- покупка и продажа валют;
- просмотр портфеля и его общей стоимости;
- получение курсов валют из локального кеша.

---

## Структура проекта

finalproject_startseva_m25-555/
├── data/
│ ├── users.json
│ ├── portfolios.json
│ └── rates.json
├── valutatrade_hub/
│ ├── core/
│ │ ├── models.py
│ │ ├── usecases.py
│ │ └── utils.py
│ └── cli/
│ └── interface.py
├── main.py
├── Makefile
├── pyproject.toml
└── README.md

---

## Основные сущности

- **User** — пользователь с хешированным паролем (SHA-256 + salt).
- **Wallet** — кошелёк одной валюты с балансом и операциями пополнения/списания.
- **Portfolio** — портфель пользователя, содержащий набор кошельков.

---

## CLI-команды

```bash
register --username alice --password 1234
login --username alice --password 1234
show-portfolio
show-portfolio --base EUR
buy --currency BTC --amount 0.05
sell --currency BTC --amount 0.01
get-rate --from BTC --to USD
```

---

## Запуск проекта

Установка зависимостей:
```bash
poetry install
```

Запуск приложения:
```bash
make project
```

## Примечание
- Курсы валют хранятся в локальном файле rates.json.