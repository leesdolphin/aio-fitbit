import asyncio
from collections import OrderedDict
import csv
import datetime
import logging

from .api import FitbitApi
from .secrets import find_secret_file, parse_secret_file


def main():
    path = find_secret_file('.')
    secrets = parse_secret_file(path)
    loop = asyncio.get_event_loop()
    # logging.basicConfig(level=logging.DEBUG)
    # logging.captureWarnings(True)
    # loop.set_debug(True)
    try:
        loop.run_until_complete(async_main(secrets))
    finally:
        loop.close()


loaded_data, loaded_days = load_numpy_data()


@asyncio.coroutine
def download_hr_data(api, date):
    if date in loaded_days:
        print("Already got data for", date)
        # Already loaded. Ignore.
        return
    try:
        _, intraday = yield from api.intraday_heartrate(date=date)
    except Exception as ex:
        print(date, 'download_hr_data EX:', ex.__class__.__qualname__)
        if str(ex):
            print(ex)
        else:
            logging.exception('Unknown Exception')
        return
    loaded_data.update((datetime.datetime.combine(date, time), value) for time, value in intraday.items())
    loaded_days.add(date)
    save_data()
    print("Loaded date", date)


@asyncio.coroutine
def async_main(secrets):
    client = secrets.create_oauth_client()
    api = FitbitApi(client=client)
    start_date = datetime.date(2016, 6, 1)
    day_count = (datetime.date.today() - start_date).days
    yield from asyncio.gather(*[
        download_hr_data(api, date)
        for date in (start_date + datetime.timedelta(n) for n in range(day_count))
    ])


if __name__ == '__main__':
    main()
