import asyncio
import datetime

from . import ALL_SCOPES
from .server import OAuth2Server

# def ensure_scopes(secrets, min_scopes, browser_authorize=False):
#     """
#     Ensures the given user keys are valid and have access to the given scopes.
#
#     If `browser_authorize` is true; then instead of raising a
#      `MissingScopeException`, or a `UserKeysInvalidException`, this function
#      will open a browser window to perform the required authentication handshake
#      before continuing. Note that even with `browser_authorize` set to truthy,
#      this function may still raise those exceptions if the user cancels; the
#      request times out, or the user limits the scopes.
#     """
#
#
#
# def request_scopes(secrets, min_scopes):
#     """
#     Authorises the application and requests the given scopes
#
#     This function will ensure that the user
#     If the client already has the requested scopes, then this function will be a no-op
#     """


def get_user_credentials(response_dict, auth_start=None):
    auth_start = auth_start or datetime.datetime.now()
    return dict(
        access_token=response_dict['access_token'],
        refresh_token=response_dict['refresh_token'],
        expiry=auth_start + datetime.timedelta(seconds=response_dict['expires_in']),
        scopes=response_dict['scope'].split(' '),
    )


@asyncio.coroutine
def browser_authorize(secrets, *, scopes=ALL_SCOPES, timeout=60):
    before_auth = datetime.datetime.now()
    client = secrets.client_secrets
    server = OAuth2Server(client.id, client.secret)
    access_token, other_info = yield from asyncio.wait_for(server.browser_authorize(), timeout=timeout)
    print("USER SECRETS", secrets.user_credentials)
    secrets.user_credentials = get_user_credentials(other_info, auth_start=before_auth)
    print("USER SECRETS", secrets.user_credentials)
    return secrets
