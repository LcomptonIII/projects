from types import SimpleNamespace
import pytest

from src.crunchyroll.history import CRHistory, CRHistoryFetchError, PAGE_SIZE


def _item(n):
    return {
        "date_played": "2026-10-01T00:00:00Z",
        "fully_watched": True,
        "panel": {
            "id": f"ep-{n}",
            "title": f"Episode {n}",
            "episode_metadata": {
                "series_id": "series-1",
                "series_title": "Test Show",
                "season_number": 1,
                "episode_number": n,
            },
        },
    }


class FakeResponse:
    def __init__(self, payload, ok=True, status_code=200, text=""):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = text
    def json(self):
        return self._payload


def _history(responses):
    h = CRHistory(SimpleNamespace(access_token="token", account_id="acct"))
    calls = []
    def get(url, params=None, timeout=None):
        calls.append((url, params, timeout))
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    h.session.get = get
    return h, calls


def test_cursor_pagination_follows_meta_next_page_without_numbered_page():
    h, calls = _history([
        FakeResponse({"data": [_item(1)], "meta": {"next_page": "/content/v2/acct/watch-history?cursor=opaque-1&page_size=100"}}),
        FakeResponse({"data": [_item(2)], "meta": {"next_page": ""}}),
    ])
    eps = h.fetch_all("en-US")
    assert [e.episode_id for e in eps] == ["ep-1", "ep-2"]
    assert calls[0][1] == {"page_size": PAGE_SIZE, "locale": "en-US"}
    assert "page" not in calls[0][1]
    assert calls[1][1] is None
    assert "cursor=opaque-1" in calls[1][0]


def test_fetch_all_preserves_partial_episodes_on_later_page_failure():
    h, _ = _history([
        FakeResponse({"data": [_item(1), _item(2)], "meta": {"next_page": "/content/v2/acct/watch-history?cursor=next"}}),
        FakeResponse({}, ok=False, status_code=503, text="temporary failure"),
    ])
    with pytest.raises(CRHistoryFetchError) as exc:
        h.fetch_all()
    assert [e.episode_id for e in exc.value.partial_episodes] == ["ep-1", "ep-2"]
    assert "503" in str(exc.value)


def test_repeated_cursor_is_rejected_instead_of_looping_forever():
    nxt = "/content/v2/acct/watch-history?cursor=same"
    h, _ = _history([
        FakeResponse({"data": [_item(1)], "meta": {"next_page": nxt}}),
        FakeResponse({"data": [_item(2)], "meta": {"next_page": nxt}}),
    ])
    with pytest.raises(CRHistoryFetchError) as exc:
        h.fetch_all()
    assert len(exc.value.partial_episodes) == 2
    assert "repeated pagination cursor" in str(exc.value)


def test_empty_next_page_ends_even_when_page_is_full():
    h, calls = _history([
        FakeResponse({"data": [_item(i) for i in range(1, PAGE_SIZE + 1)], "meta": {"next_page": None}}),
    ])
    eps = h.fetch_all()
    assert len(eps) == PAGE_SIZE
    assert len(calls) == 1
