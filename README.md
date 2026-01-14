# Final Project - Валютный кошелек

CLI-приложение для симуляции торговли валютами с локальным хранением данных.

Проект реализует Core Service платформы ValutaTrade Hub и позволяет пользователям
регистрироваться, управлять валютным портфелем, покупать и продавать валюты по текущим курсам.

---

## Функциональность

- регистрация и аутентификация пользователей
- хранение пользователей и портфелей в JSON-хранилище
- управление валютными кошельками
- покупка и продажа валют с валидацией входных данных
- автоматическое создание кошелька при покупке новой валюты
- получение и кеширование курсов валют с учётом TTL
- логирование ключевых действий пользователя
- обработка и проброс доменных исключений
- обновление курсов из внешних API (CoinGecko, ExchangeRate-API) через Parser Service  
- просмотр актуальных курсов из локального кеша (`show-rates`)

---

## Структура проекта

```bash
finalproject_startseva_m25-555/
├── data/
│   ├── users.json
│   ├── portfolios.json
│   ├── rates.json
│   └── exchange_rates.json
├── valutatrade_hub/
│   ├── __init__.py
│   ├── decorators.py
│   ├── logging_config.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── exceptions.py
│   │   ├── usecases.py
│   │   ├── currencies.py
│   │   └── utils.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── interface.py
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── settings.py
│   └── parser_service/
│       ├── __init__.py
│       ├── config.py
│       ├── api_clients.py
│       ├── updater.py
│       ├── storage.py
│       └── scheduler.py
├── .gitignore
├── main.py
├── Makefile
├── poetry.lock
├── pyproject.toml
└── README.md
```

---

## Основные сущности

- **User** — пользователь с хешированным паролем (SHA-256 + salt)
- **Wallet** — кошелёк одной валюты с балансом и операциями пополнения/списания
- **Portfolio** — портфель пользователя, содержащий набор кошельков
- **Currency** — описание валюты и её иерархии (fiat / crypto)

---

## Parser Service и обновление курсов

Отдельный Parser Service отвечает за получение и обновление курсов валют из двух внешних источников:

- CoinGecko — криптовалюты (BTC, ETH, SOL)
- ExchangeRate-API — фиатные валюты (EUR, GBP, RUB) относительно USD

Курсы приводятся к единому формату и сохраняются в:

- ```data/exchange_rates.json``` — история измерений (журнал)
- ```data/rates.json``` — актуальный кэш для Core Service

Основные элементы:

- ```config.py``` — хранит настройки (списки валют, URL, пути к файлам, таймауты, загрузка API-ключа из переменных окружения)
- ```api_clients.py``` — клиенты CoinGecko и ExchangeRate-API с обработкой сетевых ошибок и валидацией ответов
- ```updater.py``` — объединяет данные от всех клиентов, обновляет кэш и журнал, логирует шаги
- ```storage.py``` — атомарная запись JSON-файлов, работа с историей и текущим срезом курсов

Для работы ExchangeRate-API требуется ключ в переменной окружения:

```bash
export EXCHANGERATE_API_KEY="ВАШ_КЛЮЧ"
```

---

**Бизнес-операции (use cases)**

**Покупка валюты (`buy`)**
- валидация суммы (`amount > 0`)
- валидация валюты через `get_currency`
- автоматическое создание кошелька
- пополнение баланса
- расчёт оценочной стоимости в USD
- логирование операции

**Продажа валюты (`sell`)**
- валидация входных данных
- проверка наличия кошелька и достаточности средств
- списание средств
- расчёт оценочной выручки в USD
- логирование операции

**Получение курса (`get_rate`)**
- валидация валютных кодов
- проверка актуальности кеша по TTL
- попытка обновления курсов при истечении TTL
- возврат значения курса и времени обновления

**Исключения**

В проекте используются доменные исключения
- `CurrencyNotFoundError `— неизвестная валюта
- `InvalidAmountError` — некорректная сумма
- `InsufficientFundsError` — недостаточно средств
- `ApiRequestError` — ошибка обновления курсов
- `StorageError` — ошибка работы с хранилищем

Исключения генерируются в Core-слое и обрабатываются в CLI

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

## Команды работы с курсами:

```bash
update-rates
show-rates --top 10
show-rates --currency EUR
get-rate --from EUR --to USD
```

Примеры:

```bash
> update-rates
INFO: Starting rates update...
Update successful. Total rates updated: 6. Last refresh: 2026-01-14T15:14:15Z

> show-rates --top 3
Rates from cache (updated at 2026-01-14T15:14:15Z):
- BTC_USD: 96823.00
- ETH_USD: 3353.14
- SOL_USD: 146.84
```

---

## Запись демонстрации работы CLI

[![asciicast](https://asciinema.org/a/cji59t1xyfCb9Fc1.svg)](https://asciinema.org/a/cji59t1xyfCb9Fc1)

---

## Запуск проекта

Установка зависимостей:
```bash
make install
```

Запуск приложения:
```bash
make project
```

Перед работой с фиатными курсами нужно задать ключ:
```bash
export EXCHANGERATE_API_KEY="ВАШ_КЛЮЧ"
```

## Примечание
- Данные хранятся локально в JSON-файлах
- Курсы валют кешируются с использованием TTL
- Все операции чтения/изменения данных выполняются безопасно
(чтение → модификация → запись)