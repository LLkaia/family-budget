import asyncio
import logging
import sys
from time import sleep

from core.database import is_db_alive


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())

RETRIES = 100
SLEEP = 2


if __name__ == "__main__":
    for _ in range(RETRIES):
        if asyncio.run(is_db_alive()):
            log.info("Database is up and running.")
            break
        log.info("Database is down...")
        sleep(SLEEP)
    else:
        log.error(f"Database is still down after {RETRIES * SLEEP} seconds.")
        sys.exit(1)
