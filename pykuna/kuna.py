import asyncio
import logging

from .camera import KunaCamera
from .errors import AuthenticationError

API_URL = "https://server.kunasystems.com/api/v1"
AUTH_ENDPOINT = "account/auth"
CAMERAS_ENDPOINT = "user/cameras"
RECORDINGS_ENDPOINT = "recordings"

USER_AGENT = "Kuna/2.4.4 (iPhone; iOS 12.1; Scale/3.00)"
USER_AGENT_THUMBNAIL = "Kuna/156 CFNetwork/975.0.3 Darwin/18.2.0"

KUNA_STREAM_URL = "wss://server.kunasystems.com/ws/rtsp/proxy"

# The Kuna API used to answer 403 to an expired token; it now answers 401.
TOKEN_REJECTED_STATUSES = (401, 403)

_LOGGER = logging.getLogger(__name__)


class KunaAPI:
    """Class for interacting with the Kuna API."""

    def __init__(self, username, password, websession):
        """Initialize the API object."""
        self._username = username
        self._password = password
        self._websession = websession
        self._token = None
        self._auth_lock = asyncio.Lock()
        self.cameras = {}

    async def authenticate(self):
        """Login and get an auth token."""
        json = {"email": self._username, "password": self._password}

        result = await self._request("post", AUTH_ENDPOINT, json=json)

        try:
            self._token = result["token"]
        except TypeError:
            raise AuthenticationError(
                "No Kuna API token response returned, check username and password."
            )
        except KeyError as err:
            _LOGGER.error("Error retrieving Kuna auth token: {}".format(err))
            raise err

    async def update(self):
        """Refresh the dict of all cameras in the Kuna account."""
        result = await self._request("get", CAMERAS_ENDPOINT)

        if result is not None:
            new_cameras = {}

            for item in result["results"]:
                new_cameras[item["serial_number"]] = KunaCamera(item, self._request)

            self.cameras = new_cameras

    async def _request(
        self, method, path, params=None, json=None, image=False, allow_redirects=True
    ):
        """Make an async API request, logging in again once if the token is rejected.

        Cameras and recordings receive this bound method, so their calls retry too.
        """
        args = (method, path, params, json, image, allow_redirects)
        rejected_token = self._token
        try:
            return await self._send(*args)
        except _TokenRejected:
            pass

        async with self._auth_lock:
            # Another request may already have refreshed the token.
            if self._token == rejected_token:
                _LOGGER.warning("Kuna API rejected the token; re-authenticating.")
                try:
                    await self.authenticate()
                except Exception as err:
                    _LOGGER.error("Kuna re-authentication failed: {}".format(err))
                    return None

        try:
            return await self._send(*args)
        except _TokenRejected:
            _LOGGER.error("Kuna API rejected a freshly issued token: {}".format(path))
            return None

    async def _send(self, method, path, params, json, image, allow_redirects):
        """Send one API request; raise _TokenRejected if the token is not accepted."""
        from aiohttp import ClientResponseError

        url = "{}/{}/".format(API_URL, path)
        headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}

        if self._token:
            headers["Authorization"] = "Token {}".format(self._token)

        if image or not allow_redirects:
            headers["User-Agent"] = USER_AGENT_THUMBNAIL

        try:
            async with self._websession.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
                allow_redirects=allow_redirects,
            ) as result:

                result.raise_for_status()
                if image:
                    return await result.read()
                elif not allow_redirects:
                    return result
                else:
                    return await result.json()

        except ClientResponseError as err:
            # A rejected login is bad credentials, not a stale token.
            if err.status in TOKEN_REJECTED_STATUSES and path != AUTH_ENDPOINT:
                raise _TokenRejected from err
            _LOGGER.error("Kuna API request error: {}".format(err))
            return None


class _TokenRejected(Exception):
    """Raised by KunaAPI._send when the API rejects the current token."""
