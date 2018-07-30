import asyncio
import random
import string
import sys
import traceback
import webbrowser

from aiohttp import web

from aio_fitbit.oauth.client import FitbitOauth2Client


class OAuth2Server(web.View):

    PORT = 8484

    def __init__(self, client_id, client_secret):
        """ Initialize the FitbitOauth2Client """
        self.success_html = """
            <h1>You are now authorized to access the Fitbit API!</h1>
            <br/><h3>You can close this window</h3>"""
        self.failure_html = """
            <h1>ERROR: %s</h1><br/><h3>You can close this window</h3>%s"""
        self.oauth = FitbitOauth2Client(client_id, client_secret)
        self._srv = self._app = self._handler = None
        self._server_waiter = None
        self._csrf_token = None

    @asyncio.coroutine
    def _init_app(self, app):
        app.router.add_get('/', self.get)

    def _generate_csrf_token(self):
        token_alphabet = string.digits + string.ascii_letters
        self._csrf_token = ''.join(random.choice(token_alphabet) for _ in range(random.randint(40, 50)))
        return self._csrf_token

    def _validate_csrf_token(self, given_token):
        if not given_token or not self._csrf_token:
            return False
        result = True
        # Safe against
        for idx, given in enumerate(given_token):
            if idx < len(self._csrf_token) and given != self._csrf_token[idx]:
                result = False
        result = result and len(given_token) == len(self._csrf_token)
        return result

    def redirect_uri(self):
        return 'http://127.0.0.1:%s/' % (self.PORT, )

    @asyncio.coroutine
    def browser_authorize(self, scopes=None):
        """Start the server and open the web browser to complete auth."""
        if self._server_waiter:
            return (yield from self._server_waiter)
        self._server_waiter = asyncio.Future()
        try:
            self._app = app = web.Application()
            yield from self._init_app(app)
            self._handler = handler = app.make_handler()
            yield from app.startup()
            print("Starting server")
            srv = yield from asyncio.get_event_loop().create_server(handler, '127.0.0.1', self.PORT)
            print("Starting sfdf")
            yield from asyncio.sleep(1)
            self._srv = srv
            self.auth_params = dict(
                redirect_uri=self.redirect_uri(),
                state=self._generate_csrf_token()
            )
            extra_params = dict()
            if scopes is not None:
                extra_params['scopes'] = scopes
            url = self.oauth.get_authorize_url(**self.auth_params)
            webbrowser.open(url)
            return (yield from self._server_waiter)
        except Exception as e:
            if not self._server_waiter.done():
                self._server_waiter.set_exception(e)
            raise e
        finally:
            yield from self.shutdown_server()

    @asyncio.coroutine
    def shutdown_server(self, cancel_waiter=True):
        try:
            print('srv')
            if self._srv:
                self._srv.close()
                yield from self._srv.wait_closed()
            print('app')
            if self._app:
                yield from self._app.shutdown()
            print('handler')
            if self._handler:
                yield from self._handler.finish_connections(1)
            print('app_clean')
            if self._app:
                yield from self._app.cleanup()
            print('done')
        except BaseException as e:
            self._server_waiter.set_exception(e)
            raise
        finally:
            self._srv = self._app = self._handler = None
            if self._server_waiter and not self._server_waiter.done() and cancel_waiter:
                self._server_waiter.cancel()

    def schedule_shutdown_and_close(self, *, exception=None, result=None):
        if exception is result is None:
            raise ValueError('Specify either an exception or result')
        if exception is not None and result is not None:
            raise ValueError("Specify exactly one of exception or result")

        @asyncio.coroutine
        def delayed_call():
            print("Requesting shutdown")
            try:
                yield from self.shutdown_server(cancel_waiter=False)
            except BaseException as e:
                self._server_waiter.set_exception(e)
            else:
                if exception is not None:
                    self._server_waiter.set_exception(exception)
                else:
                    self._server_waiter.set_result(result)
            print("Server shutdown.", dict(result=result, exception=exception))
        asyncio.ensure_future(delayed_call())

    @asyncio.coroutine
    def get(self, request, **k):
        try:
            # Check CSRF first
            if not self._validate_csrf_token(request.GET.get('state', None)):
                yield from asyncio.sleep(random.uniform(0, 0.5))
                raise web.HTTPBadRequest(text='Request invalid. Please try again in a moment.')
            code = request.GET.get('code', None)
            token, data = yield from self.oauth.get_access_token(code, **self.auth_params)
            self.schedule_shutdown_and_close(result=(token, data))
            return web.Response(text="You are authenticated.")
        except web.HTTPError as e:
            # Requesting access token failed.
            self._server_waiter.set_exception(e)
            raise e

    def _fmt_failure(self, message):
        tb = traceback.format_tb(sys.exc_info()[2])
        tb_html = '<pre>%s</pre>' % ('\n'.join(tb)) if tb else ''
        return self.failure_html % (message, tb_html)
