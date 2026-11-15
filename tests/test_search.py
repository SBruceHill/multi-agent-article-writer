import json

import pytest
from conftest import invoke_tool
from ddgs.exceptions import DDGSException

from article_writer.config import NUM_RESULTS
from article_writer.tools import fetch, search


def make_results(n, start=0):
    return [{"title": f"t{i}", "href": f"https://site{i}.com/a", "body": "b"}
            for i in range(start, start + n)]


@pytest.fixture
def sleeps(monkeypatch):
    """Record sleeps instead of waiting."""
    recorded = []
    monkeypatch.setattr(search.time, "sleep", recorded.append)
    return recorded


def script_pages(monkeypatch, *pages):
    """Make throttled_text return the given pages in order; an Exception instance is raised."""
    queue = list(pages)

    def fake(query, page):
        item = queue.pop(0) if queue else []
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(search, "throttled_text", fake)


def test_full_first_page_needs_no_retry(monkeypatch, sleeps):
    script_pages(monkeypatch, make_results(NUM_RESULTS))
    outcome = search.search_with_backoff("q")
    assert len(outcome.results) == NUM_RESULTS
    assert sleeps == []


def test_backs_off_exponentially_then_succeeds(monkeypatch, sleeps):
    script_pages(monkeypatch, DDGSException("rate limit"), DDGSException("rate limit"),
                 make_results(NUM_RESULTS))
    outcome = search.search_with_backoff("q")
    assert len(outcome.results) == NUM_RESULTS
    assert sleeps == [2, 4]


def test_pages_until_enough_results_and_dedupes(monkeypatch, sleeps):
    script_pages(monkeypatch, make_results(6), make_results(6, start=4))
    outcome = search.search_with_backoff("q")
    assert [r["href"] for r in outcome.results] == [f"https://site{i}.com/a" for i in range(NUM_RESULTS)]
    assert sleeps == []


def test_keeps_best_partial_results_after_all_retries(monkeypatch, sleeps):
    script_pages(monkeypatch, make_results(3), DDGSException("boom"), [])
    outcome = search.search_with_backoff("q")
    assert len(outcome.results) == 3
    assert sleeps == [2, 4]


def test_gives_up_with_error_after_three_attempts(monkeypatch, sleeps):
    script_pages(monkeypatch, DDGSException("a"), DDGSException("b"), DDGSException("c"))
    outcome = search.search_with_backoff("q")
    assert outcome.results == []
    assert str(outcome.error) == "c"


def test_tool_wiring_returns_json_and_flags_blocked_domains(monkeypatch, sleeps):
    script_pages(monkeypatch, make_results(NUM_RESULTS))
    fetch.BLOCKED_DOMAINS.add("site1.com")
    results = json.loads(invoke_tool(search.search_web, query="q"))
    flagged = [r["href"] for r in results if r.get("fetchable") is False]
    assert flagged == ["https://site1.com/a"]


def test_tool_wiring_failure_message(monkeypatch, sleeps):
    script_pages(monkeypatch, [], [], [])
    output = invoke_tool(search.search_web, query="cats")
    assert output == ("Search for 'cats' failed (No results found.). "
                      "Try a different or broader query.")


def test_throttled_text_spaces_requests(monkeypatch):
    clock = iter([100.0, 100.5, 101.0])
    sleeps = []
    monkeypatch.setattr(search.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(search.time, "sleep", sleeps.append)
    monkeypatch.setattr(search, "_last_search_time", 99.0)
    monkeypatch.setattr(search, "ddgs", type("D", (), {"text": lambda self, *a, **k: ["r"]})())
    assert search.throttled_text("q", 1) == ["r"]
    assert sleeps == [pytest.approx(search.MIN_SEARCH_INTERVAL - 1.0)]


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


@pytest.fixture
def brave(monkeypatch):
    """Set a fake key and capture requests.get calls; returns (calls, set_response)."""
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    monkeypatch.setattr(search.time, "sleep", lambda s: None)
    state = {"calls": [], "response": FakeResponse()}

    def fake_get(url, **kwargs):
        state["calls"].append((url, kwargs))
        r = state["response"]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(search.requests, "get", fake_get)
    return state


def test_brave_results_are_mapped_to_ddgs_shape(brave):
    brave["response"] = FakeResponse(payload={"web": {"results": [
        {"title": "T", "url": "https://a.com/1", "description": "a <strong>bold</strong> claim"}]}})
    assert search.brave_text("q", 2) == [{"title": "T", "href": "https://a.com/1", "body": "a bold claim"}]
    url, kwargs = brave["calls"][0]
    assert url == search.BRAVE_URL
    assert kwargs["headers"]["X-Subscription-Token"] == "test-key"
    assert kwargs["params"] == {"q": "q", "count": NUM_RESULTS, "offset": 1}


def test_brave_non_200_raises(brave):
    brave["response"] = FakeResponse(status_code=429)
    with pytest.raises(search.BraveError, match="HTTP 429"):
        search.brave_text("q", 1)


def test_throttled_text_uses_brave_when_key_is_set(brave, monkeypatch):
    brave["response"] = FakeResponse(payload={"web": {"results": [{"title": "T", "url": "https://a.com"}]}})
    monkeypatch.setattr(search, "ddgs", None)  # would crash if ddgs were used
    assert search.throttled_text("q", 1)[0]["href"] == "https://a.com"


def test_throttled_text_falls_back_to_ddgs_when_brave_fails(brave, monkeypatch):
    brave["response"] = search.requests.ConnectionError("down")
    monkeypatch.setattr(search, "ddgs", type("D", (), {"text": lambda self, *a, **k: ["from-ddgs"]})())
    assert search.throttled_text("q", 1) == ["from-ddgs"]


def test_throttled_text_skips_brave_without_a_key(monkeypatch):
    monkeypatch.setattr(search.time, "sleep", lambda s: None)
    monkeypatch.setattr(search, "ddgs", type("D", (), {"text": lambda self, *a, **k: ["from-ddgs"]})())
    assert search.throttled_text("q", 1) == ["from-ddgs"]
