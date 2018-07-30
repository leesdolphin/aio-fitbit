from collections import namedtuple
import datetime
import warnings

from frozenordereddict import FrozenOrderedDict

from aio_fitbit.apis._base import ApiBase, ApiEndpoint
from aio_fitbit.exceptions import FitbitApiWarning


class HeartrateZone(namedtuple('HeartrateZone', ['calories_out', 'min', 'max', 'minutes', 'name'])):

    @classmethod
    def build_from_response(cls, zone_dict):
        return cls(
            calories_out=zone_dict.get('caloriesOut', None),
            min=zone_dict.get('min', None),
            max=zone_dict.get('max', None),
            minutes=zone_dict.get('minutes', None),
            name=zone_dict.get('name', None),
        )


class HeartrateResult(namedtuple('HeartrateResult', ['heart_rate_zones', 'custom_heart_rate_zones', 'resting_heart_rate'])):

    @classmethod
    def build_from_response(cls, heart_rate_day_dict):
        heart_rate_zones = []
        for zone in heart_rate_day_dict['heartRateZones']:
            heart_rate_zones.append(HeartrateZone.build_from_response(zone))
        custom_heart_rate_zones = []
        for zone in heart_rate_day_dict['customHeartRateZones']:
            custom_heart_rate_zones.append(HeartrateZone.build_from_response(zone))
        if 'restingHeartRate' in heart_rate_day_dict:
            resting_heart_rate = int(heart_rate_day_dict['restingHeartRate'])
        else:
            resting_heart_rate = None
        return cls(
            heart_rate_zones=tuple(heart_rate_zones),
            custom_heart_rate_zones=tuple(custom_heart_rate_zones),
            resting_heart_rate=resting_heart_rate,
        )


class HeartrateResults(FrozenOrderedDict):

    @classmethod
    def build_from_response(cls, heart_respones_list):
        parsed_tuples = []
        for entry in heart_respones_list:
            date = datetime.datetime.strptime(entry['dateTime'], '%Y-%m-%d').date()
            value = HeartrateResult.build_from_response(entry['value'])
            parsed_tuples.append((date, value))
        return cls(parsed_tuples)


class IntradayHeartrateResults(FrozenOrderedDict):

    __slots__ = ('_interval', '_interval_type')

    @classmethod
    def build_from_response(cls, intraday_respones_dict):
        dataset = intraday_respones_dict.get('dataset', [])
        parsed_tuples = []
        for entry in dataset:
            value = entry['value']
            time = datetime.datetime.strptime(entry['time'], '%H:%M:%S').time()
            parsed_tuples.append((time, value))
        return cls(
            dataset=parsed_tuples,
            interval=intraday_respones_dict['datasetInterval'],
            interval_type=intraday_respones_dict['datasetType'],
        )

    def __init__(self, dataset, interval, interval_type):
        super().__init__(dataset)
        self._interval = interval
        self._interval_type = interval_type

    @property
    def interval(self):
        return self._interval

    def interval_type(self):
        return self._interval_type

    def interval_timedelta(self):
        return None

    def __repr__(self):
        items = self.items()
        if len(items) > 5:
            itemsiter = iter(items)
            items = []
            for _ in range(5):
                items.append(next(itemsiter))
            items = repr(items)
            items = items[:-1] + ', <...>' + items[-1]
        else:
            items = repr(list(items))
        return '{}({})'.format(self.__class__.__name__, items)

    # def __eq__(self, other):
    #     return (
    #         other.interval == self._interval and
    #         other.interval_type == self._interval_type and
    #         super().__eq__(other)
    #     )
    #
    # def __hash__(self):
    #     return super().__hash__() + hash((
    #         self._interval, self._interval_type
    #     ))

    # def get_subset(self, start_time=None, end_time=None):


class IntradayHeartrateEndpoint(ApiEndpoint):

    BASE_URL = 'user/-/activities/heart/date/'
    DETAIL_LEVELS = ('1sec', '1min')
    DATE_FORMAT = '%Y-%m-%d'
    TIME_FORMAT = '%H:%M'

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        assert self.api_base._user == '-'

    def build_url(self, date, detail_level='1sec', end_date=None, start_time=None, end_time=None):
        if end_date is not None:
            if end_date == date:
                # They point to the same day; so use the '1d' endpoint.
                end_date = None
            else:
                # These are not valid for ranges of more than 1 day.
                assert start_time is None
                assert end_time is None
        if start_time is not None and end_time is None:
            warnings.warn('Giving `start_time` without `end_time` will not '
                          'include data for 23:59:**', FitbitApiWarning)
            end_time = datetime.time.max
        elif end_time is not None and start_time is None:
            start_time = datetime.time.min
        assert detail_level in self.DETAIL_LEVELS

        url_parts = [date.strftime(self.DATE_FORMAT)]
        if end_date:
            url_parts.append(end_date.strftime(self.DATE_FORMAT))
        else:
            url_parts.append('1d')
        url_parts.append(detail_level)
        if start_time:
            url_parts.append('time')
            url_parts.append(start_time.strftime(self.TIME_FORMAT))
            url_parts.append(end_time.strftime(self.TIME_FORMAT))
        return super().build_url(url_parts)

    def parse_response_json(self, response_json):
        intraday_results = None
        if 'activities-heart-intraday' in response_json:
            intraday_results = IntradayHeartrateResults.build_from_response(response_json['activities-heart-intraday'])
        if 'activities-heart' in response_json:
            heartrate_results = HeartrateResults.build_from_response(response_json['activities-heart'])
        return (
            heartrate_results,
            intraday_results
        )


class Heartrate(ApiBase):

    intraday_heartrate = IntradayHeartrateEndpoint.as_api()
