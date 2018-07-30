import asyncio
from collections import namedtuple
import datetime
import pathlib

import aiohttp
import yaml

from aio_fitbit.oauth.client import FitbitOauth2Client
from aio_fitbit.oauth.utils import get_user_credentials
from aio_fitbit.exceptions import FitbitApiLimitExceededException


def find_secret_file(cwd, valid_filenames=('.fitbit.secret', '.fitbit.secret.yaml'), multicase=True):
    cwd = pathlib.Path(cwd).resolve()
    if multicase:
        valid_filenames = frozenset(name.lower() for name in valid_filenames)
    else:
        valid_filenames = frozenset(valid_filenames)
    for path in [cwd] + list(cwd.parents):
        for file in path.iterdir():
            if file.is_file():
                name = file.name
                if multicase:
                    name = name.lower()
                if name in valid_filenames:
                    return file
    return None


def parse_secret_file(filename):
    filename = pathlib.Path(filename)
    data = SecretsFile(filename)
    data.load()
    return data


ClientSecrets = namedtuple('ClientSecrets', ('id', 'secret'))
ClientSecrets.EMPTY = ClientSecrets('', '')

UserCredentials = namedtuple('UserCredentials', ('access_token', 'refresh_token', 'expiry', 'scopes'))
UserCredentials.EMPTY = UserCredentials('', '', datetime.datetime.fromtimestamp(0), ())

ApiUsage = namedtuple('ApiUsage', ('remaining', 'reset'))
ApiUsage.EMPTY = ApiUsage(0, datetime.datetime.fromtimestamp(0))


class SecretsFile():

    def __init__(self, filename):
        self.filename = str(filename)
        self._client_secrets = ClientSecrets.EMPTY
        self._user_credentials = UserCredentials.EMPTY
        self._api_usage = ApiUsage.EMPTY
        self._is_loaded = False

    @property
    def client_secrets(self):
        self.ensure_loaded()
        return self._client_secrets

    @client_secrets.setter
    def client_secrets(self, secrets):
        if isinstance(secrets, dict):
            self._client_secrets = ClientSecrets.EMPTY._replace(**secrets)
        else:
            self._client_secrets = ClientSecrets._make(secrets)

    @property
    def user_credentials(self):
        self.ensure_loaded()
        return self._user_credentials

    @user_credentials.setter
    def user_credentials(self, secrets):
        if isinstance(secrets, dict):
            self._user_credentials = UserCredentials.EMPTY._replace(**secrets)
        else:
            self._user_credentials = UserCredentials._make(secrets)

    @property
    def api_usage(self):
        self.ensure_loaded()
        return self._api_usage

    @api_usage.setter
    def api_usage(self, secrets):
        if isinstance(secrets, dict):
            self._api_usage = ApiUsage.EMPTY._replace(**secrets)
        else:
            self._api_usage = ApiUsage._make(secrets)

    def create_oauth_client(self):
        return SecretsBackedFitbitApiClient(self)

    def ensure_loaded(self):
        if not self._is_loaded:
            self.load()

    def load(self, filename=None):
        if filename is None:
            filename = self.filename
        with open(filename, 'r') as file:
            data = yaml.safe_load(file)
        print(data)
        if 'client' in data:
            self.client_secrets = data['client']
        if 'user' in data:
            self.user_credentials = data['user']
        if 'api' in data:
            self.api_usage = data['api']
        self._is_loaded = True

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        data = {
            'client': dict(self.client_secrets._asdict()),
            'user': dict(self.user_credentials._asdict()),
            'api': dict(self.api_usage._asdict()),
        }
        with open(filename, 'w') as file:
            yaml.safe_dump(data, file)


class SecretsBackedFitbitApiClient(FitbitOauth2Client):

    def __init__(self, secret_store, action_on_expended_rate_limit='ignore'):
        self.secret_store = secret_store
        self.refresh_token_future = None

    @property
    def client_id(self):
        return self.secret_store.client_secrets.id

    @property
    def client_secret(self):
        return self.secret_store.client_secrets.secret

    @property
    def access_token(self):
        return self.secret_store.user_credentials.access_token

    @asyncio.coroutine
    def _handle_error_response_single(self, err_type, error_data):
        if err_type == 'expired_token':
            return (yield from self.refresh_token())

    @asyncio.coroutine
    def refresh_token(self):
        if self.refresh_token_future:
            return (yield from self.refresh_token_future)
        else:
            try:
                self.refresh_token_future = asyncio.ensure_future(self._do_refresh_token())
                return (yield from self.refresh_token_future)
            finally:
                self.refresh_token_future = None

    def _do_refresh_token(self):
        print("Refresh Token")
        method = 'POST'
        url = 'https://api.fitbit.com/oauth2/token'
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.secret_store.user_credentials.refresh_token,
            'expires_in': '3600',
        }
        auth_start_time = datetime.datetime.now()
        response = yield from aiohttp.request(method, url, auth=auth, data=data)
        print("REFRESH TOKEN", response)
        response_json = yield from response.json()
        print(response_json)
        if response.status >= 400:
            # Refreshing the token failed.
            return False
        resp_json = yield from response.json()
        self.secret_store.user_credentials = get_user_credentials(resp_json, auth_start=auth_start_time)
        self.secret_store.save()
        return True

    @asyncio.coroutine
    def _do_request(self, *args, **kwargs):
        req_start = datetime.datetime.now()
        if (self.secret_store.api_usage.remaining < 10 and
                self.secret_store.api_usage.reset > req_start):
            raise FitbitApiLimitExceededException('Precheck failed, retry at %s' % self.secret_store.api_usage.reset)
        response = yield from super()._do_request(*args, **kwargs)
        if ('Fitbit-Rate-Limit-Remaining' in response.headers and
                'Fitbit-Rate-Limit-Reset' in response.headers):
            remaining = int(response.headers['Fitbit-Rate-Limit-Remaining'])
            reset = datetime.timedelta(seconds=int(response.headers['Fitbit-Rate-Limit-Reset']))
            self.secret_store.api_usage = ApiUsage(remaining, req_start + reset)
            self.secret_store.save()
        if response.status == 429:
            response.close()
            print('_do_request', response.headers)
            raise FitbitApiLimitExceededException('Response status 429, retry in %s' % response.headers['Fitbit-Rate-Limit-Reset'])
        return response
