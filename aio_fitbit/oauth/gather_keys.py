import asyncio
import logging

from .utils import browser_authorize
from ..secrets import find_secret_file, parse_secret_file


def main():
    path = find_secret_file('.')
    secrets = parse_secret_file(path)
    loop = asyncio.get_event_loop()
    logging.basicConfig(level=logging.DEBUG)
    logging.captureWarnings(True)
    loop.set_debug(True)
    try:
        loop.run_until_complete(async_main(secrets))
    finally:
        loop.close()


@asyncio.coroutine
def async_main(secrets):
    secrets = yield from browser_authorize(secrets)
    secrets.save()


if __name__ == '__main__':
    main()
