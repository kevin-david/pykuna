"""KunaAPI logs in again and retries once when the API rejects its token."""
import asyncio

from aiohttp import ClientResponseError
import pytest

from pykuna import AuthenticationError, KunaAPI

GOOD_TOKEN = "good"


class FakeResponse:
    def __init__(self, status, body=None):
        self.status = status
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass

    def raise_for_status(self):
        if self.status >= 400:
            request_info = type("RequestInfo", (), {"real_url": "https://kuna.test/"})()
            raise ClientResponseError(request_info, (), status=self.status)

    async def json(self):
        return self._body


class FakeSession:
    """Accepts only GOOD_TOKEN; login issues it unless bad_credentials."""

    def __init__(self, bad_credentials=False, reject_everything=False, rejected_status=401):
        self.paths = []
        self.bad_credentials = bad_credentials
        self.reject_everything = reject_everything
        self.rejected_status = rejected_status

    def request(self, method, url, headers=None, **kwargs):
        path = url.split("/api/v1/")[1]
        self.paths.append(path)
        if path == "account/auth/":
            if self.bad_credentials:
                return FakeResponse(401)
            return FakeResponse(200, {"token": GOOD_TOKEN})
        if self.reject_everything or headers.get("Authorization") != "Token " + GOOD_TOKEN:
            return FakeResponse(self.rejected_status)
        return FakeResponse(200, {"results": []})


def stale_api(session):
    api = KunaAPI("user@example.com", "password", session)
    api._token = "stale"
    return api


@pytest.mark.parametrize("status", [401, 403])
def test_rejected_token_logs_in_again_and_retries(status):
    session = FakeSession(rejected_status=status)
    api = stale_api(session)

    result = asyncio.run(api._request("get", "user/cameras"))

    assert result == {"results": []}
    assert session.paths == ["user/cameras/", "account/auth/", "user/cameras/"]


def test_concurrent_rejections_log_in_once():
    session = FakeSession()
    api = stale_api(session)

    async def five_requests():
        return await asyncio.gather(*(api._request("get", "user/cameras") for _ in range(5)))

    results = asyncio.run(five_requests())

    assert results == [{"results": []}] * 5
    assert session.paths.count("account/auth/") == 1


def test_failed_login_returns_none_without_looping():
    session = FakeSession(bad_credentials=True)
    api = stale_api(session)

    assert asyncio.run(api._request("get", "user/cameras")) is None
    assert session.paths == ["user/cameras/", "account/auth/"]


def test_fresh_token_rejected_returns_none_after_one_retry():
    session = FakeSession(reject_everything=True)
    api = stale_api(session)

    assert asyncio.run(api._request("get", "user/cameras")) is None
    assert session.paths == ["user/cameras/", "account/auth/", "user/cameras/"]


def test_initial_login_with_bad_credentials_raises():
    api = KunaAPI("user@example.com", "password", FakeSession(bad_credentials=True))

    with pytest.raises(AuthenticationError):
        asyncio.run(api.authenticate())


def test_update_recovers_from_stale_token():
    api = stale_api(FakeSession())

    asyncio.run(api.update())

    assert api.cameras == {}
    assert api._token == GOOD_TOKEN
