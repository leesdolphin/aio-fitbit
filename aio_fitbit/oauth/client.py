import asyncio

from aioauth_client import OAuth2Client
from aiohttp import BasicAuth, request as aiorequest

from aio_fitbit import API_VERSION
from aio_fitbit.exceptions import FitbitApiException
from aio_fitbit.oauth import ALL_SCOPES


class FitbitOauth2Client(OAuth2Client):

    authorize_url = 'https://www.fitbit.com/oauth2/authorize'
    access_token_url = 'https://api.fitbit.com/oauth2/token'
    base_url = 'https://api.fitbit.com/{version}/'.format(version=API_VERSION)
    name = 'fitbit'
    user_info_url = 'https://api.fitbit.com/1/user/-/profile.json'

    DEFAULT_SCOPES = ALL_SCOPES

    def __init__(self, *a, **k):
        # Provide default FitBit scope.
        super().__init__(*a, **k)

    @staticmethod
    def user_parse(data):
        user_data = data['user']
        yield 'id', None
        yield 'gender', user_data['gender']
        yield 'username', user_data['displayName']
        yield 'first_name', user_data['fullName']
        yield 'country', user_data['country']
        yield 'city', user_data['city']
        yield 'locale', user_data['locale']
        yield 'picture', user_data['avatar']

    def get_authorize_url(self, *args, scope=None, **params):
        if scope is not None:
            if isinstance(scope, str):
                params['scope'] = scope
            else:
                params['scope'] = ' '.join(scope)
        else:
            params['scope'] = ' '.join(self.DEFAULT_SCOPES)
        return super().get_authorize_url(*args, **params)

    def _handle_error_response_single(self, err_type, error_data):
        pass

    @asyncio.coroutine
    def _handle_error_response(self, response):
        print("Handling Error Response")
        data = yield from response.json()
        errors = data.get('errors', [])
        should_retry = False
        for error in errors:
            err_type = error.get('errorType', 'unknown')
            should_retry_for_error = yield from self._handle_error_response_single(err_type, error)
            should_retry = should_retry or should_retry_for_error
        print("Handled Error Response:", should_retry)
        return should_retry

    def request(self, *args, timeout=10, loop=None, **kwargs):
        """Request OAuth2 resource."""
        # Enforce the timeout outside of the error checking/retry cycle.
        return asyncio.wait_for(self._request(*args, **kwargs), timeout, loop=loop)

    @asyncio.coroutine
    def _request(self, method, url, params=None, headers=None, loop=None, **aio_kwargs):
        url = self._get_url(url)
        print('FitbitOauth2Client._request', url)
        should_retry = True
        while should_retry:
            print("Retrying ", method, url)
            should_retry = False
            if self.access_token:
                headers = headers or {'Accept': 'application/json'}
                headers['Authorization'] = "Bearer {}".format(self.access_token)
                auth = None
            else:
                auth = BasicAuth(self.client_id, self.client_secret)
                headers = headers or {
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                }
            response = yield from self._do_request(
                method, url, params=params, headers=headers,
                auth=auth, loop=loop, **aio_kwargs
            )
            if response.status < 400:
                return response
            should_retry = yield from self._handle_error_response(response)
            if not should_retry:
                # The response's error couldn't be handled; so we'll just return
                # and let the caller deal with any errors their own way.
                return response
            response.close()

    def _do_request(self, method, url, **aio_kwargs):
        print(method, url)
        return aiorequest(method, url, **aio_kwargs)
