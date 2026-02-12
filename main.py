import argparse
import asyncio
import logging
import os
import pickle
import sys
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv

from client import LICENSES, PortalClient

STATE_FILE = "last_borrowed.pickle"


def load_state() -> Dict[str, datetime]:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "rb") as f:
        data: Any = pickle.load(f)
        if isinstance(data, dict):
            return data
        return {}


def save_state(data: Dict[str, datetime]) -> None:
    with open(STATE_FILE, "wb") as f:
        pickle.dump(data, f)


async def main() -> None:
    load_dotenv()
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("licenses", nargs="+", choices=list(LICENSES.keys()))
    args = parser.parse_args()

    email: str | None = os.getenv("LOGIN_EMAIL")
    password: str | None = os.getenv("LOGIN_PASSWORD")

    if not email or not password:
        logging.critical("Environment variables LOGIN_EMAIL or LOGIN_PASSWORD missing.")
        sys.exit(1)

    state: Dict[str, datetime] = load_state()
    client = PortalClient(email, password)

    try:
        await client.login()

        now = datetime.now()

        for item in args.licenses:
            last_date: datetime | None = state.get(item)

            max_days = LICENSES[item]["days"]

            renew_threshold = max_days - 1

            if last_date:
                days_active = (now - last_date).days
                if days_active < renew_threshold:
                    logging.info(
                        f"Skipping {item}: Active for {days_active} days (Expires in {max_days - days_active} days)."
                    )
                    continue

            if await client.borrow(item):
                logging.info(f"Successfully borrowed {item}")
                state[item] = now

        save_state(state)

    except Exception as e:
        logging.exception(f"Runtime error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
