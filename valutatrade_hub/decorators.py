import functools
import logging


def log_action(action: str, verbose: bool = False):
    """
    Логирует на INFO факт выполнения операции и ключевые параметры.
    При исключении логирует ERROR-результат и пробрасывает исключение.
    Опция verbose добавляет расширенный контекст (если доступен)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(__name__)

            user = args[0] if len(args) > 0 else kwargs.get("user")
            currency_code = args[1] if len(args) > 1 else kwargs.get("currency")
            amount = args[2] if len(args) > 2 else kwargs.get("amount")

            username = getattr(user, "username", None)
            user_id = getattr(user, "user_id", None)

            try:
                result = func(*args, **kwargs)

                rate = None
                base = None
                if isinstance(result, dict):
                    rate = result.get("rate")
                    if "cost_usd" in result or "revenue_usd" in result:
                        base = "USD"

                msg = (
                    f"{action} user='{username}' user_id={user_id} "
                    f"currency='{currency_code}' amount={amount} "
                    f"rate={rate} base='{base}' result=OK"
                )

                if verbose and isinstance(result, dict):
                    before = result.get("before")
                    after = result.get("after")
                    usd_after = result.get("usd_after")

                    if before is not None and after is not None:
                        msg += f" verbose=before->{before} after->{after}"
                    if usd_after is not None:
                        msg += f" usd_after={usd_after}"

                logger.info(msg)
                return result

            except Exception as e:
                logger.error(
                    "%s user='%s' user_id=%s currency='%s' amount=%s result=ERROR "
                    "error_type=%s error_message='%s'",
                    action,
                    username,
                    user_id,
                    currency_code,
                    amount,
                    type(e).__name__,
                    str(e),
                )
                raise

        return wrapper

    return decorator