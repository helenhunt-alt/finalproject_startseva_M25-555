# exceptions.py

class CurrencyError(Exception):
    """Базовое исключение для валют."""
    pass


class CurrencyNotFoundError(CurrencyError):
    """Валюта с указанным кодом не найдена."""
    def __init__(self, code: str):
        super().__init__(f"Неизвестная валюта '{code}'")


class CurrencyValidationError(CurrencyError):
    """Ошибка валидации валюты."""
    pass


class InsufficientFundsError(Exception):
    """Недостаточно средств на кошельке."""
    def __init__(self, code: str, available: float, required: float):
        self.code = code
        self.available = available
        self.required = required
        super().__init__(
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )


class ApiRequestError(Exception):
    """Ошибка при обращении к внешнему API (Parser Service)."""
    def __init__(self, reason: str):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")