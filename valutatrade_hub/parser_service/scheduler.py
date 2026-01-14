# scheduler.py

import logging
import time

from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler(updater: RatesUpdater, interval_seconds: int) -> None:
    logger = logging.getLogger(__name__)

    if not isinstance(interval_seconds, int) or interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive int")

    logger.info("Parser scheduler started interval_seconds=%s", interval_seconds)

    try:
        while True:
            started_ts = time.time()
            try:
                updater.run_update()
            except Exception:
                logger.exception("Parser scheduler: update cycle failed")

            elapsed = time.time() - started_ts
            sleep_for = max(0.0, interval_seconds - elapsed)

            logger.info(
                "Parser scheduler: cycle done elapsed=%.2fs next_sleep=%.2fs",
                elapsed,
                sleep_for,
            )
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        logger.info("Parser scheduler stopped (KeyboardInterrupt)")


def build_default_updater() -> RatesUpdater:
    config = ParserConfig()
    config.validate()

    clients = [
        CoinGeckoClient(config),
        ExchangeRateApiClient(config),
    ]
    return RatesUpdater(config=config, api_clients=clients, storage_module=storage)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_scheduler(build_default_updater(), interval_seconds=300)