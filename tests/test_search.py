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
