import asyncio


class ApiBase():

    def __init__(self, *, client, user='-'):
        self._client = client
        self._user = user

    @asyncio.coroutine
    def request(self, method, url, query_params=None, **kwargs):
        print('ApiBase.request', method, url, type(self._client))
        return self._client.request(method, url, **kwargs)


class ApiEndpointMetaclass(type):

    def as_api(cls, **initkwargs):
        @asyncio.coroutine
        def api(api_base_self, *args, **kwargs):
            api_instance = cls(api_base=api_base_self, **initkwargs)
            return api_instance.call(*args, **kwargs)
        return api


class ApiEndpoint(metaclass=ApiEndpointMetaclass):

    def __init__(self, *, api_base):
        self.api_base = api_base

    @asyncio.coroutine
    def call(self, *args, **kwargs):
        url = self.build_url(*args, **kwargs)
        response = yield from self.api_base.request('GET', url)
        return (yield from self.parse_response(response))

    def build_url(self, url_parts, base_url=None, extension='.json'):
        if base_url is None:
            base_url = self.BASE_URL
        url = base_url + '/'.join(url_parts) + extension
        url = url.replace('//', '/')
        return url

    @asyncio.coroutine
    def parse_response(self, response):
        if self._save_response:
            data = yield from response.text()
            filename = response.url.replace('/', '_').replace(':', '')
            with open(filename, 'w') as file:
                file.write(data)
        json = yield from response.json()
        if 'errors' in json:
            raise ValueError("Fitbit indicated request failed." + repr(json))
        return self.parse_response_json(json)

    def parse_response_json(self, json_response):
        return json_response
