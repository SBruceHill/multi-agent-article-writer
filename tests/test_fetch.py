from types import SimpleNamespace

import pytest
from conftest import invoke_tool

from article_writer.config import MIN_SOURCE_CHARS, REQUIRED_SOURCES
from article_writer.tools import fetch

LONG_TEXT = "x" * MIN_SOURCE_CHARS


def fake_response(status=200, html="<html></html>"):
    return SimpleNamespace(status=status, html=html)


@pytest.fixture
def respond(monkeypatch):
    """Mock fetch_response and trafilatura.extract; returns a list of fetched URLs."""
    calls = []

    def install(response, text=LONG_TEXT):
        def fake_fetch(url, **kwargs):
            calls.append(url)
            return response

        monkeypatch.setattr(fetch, "fetch_response", fake_fetch)
        monkeypatch.setattr(fetch.trafilatura, "extract", lambda html: text)
        return calls

    return install


@pytest.mark.parametrize("url, expected", [
    ("https://www.Example.com/a/b", "example.com"),
    ("http://news.example.com/x?y=1", "news.example.com"),
    ("https://example.com", "example.com"),
    ("https://wwwexample.com/", "wwwexample.com"),
])
def test_domain_of(url, expected):
    assert fetch.domain_of(url) == expected


def test_source_progress_asks_for_more_sources(read_urls):
    read_urls.add("https://a.com/1")
    message = fetch.source_progress(read_urls)
    assert message == (f"[Progress: 1 of {REQUIRED_SOURCES} required sources read successfully. "
                       f"Read at least {REQUIRED_SOURCES - 1} more before writing the report.]")


def test_source_progress_says_stop_when_requirement_met(read_urls):
    urls = {f"https://site{i}.com/a" for i in range(REQUIRED_SOURCES)}
    read_urls.update(urls)
    message = fetch.source_progress(read_urls)
    assert "The requirement is met" in message
    assert "STOP searching and reading" in message
    assert ", ".join(sorted(urls)) in message


def test_normalize_url_ignores_www_and_trailing_slash():
    assert fetch.normalize_url("https://www.A.com/p/") == fetch.normalize_url("https://a.com/p")


def test_source_problem_flags_missing_and_unread_sources(read_urls):
    assert "no '## Sources' section" in fetch.source_problem("just text", read_urls)
    brief = "## Sources\n[1] A - https://a.com/1"
    assert "https://a.com/1".removeprefix("https://") in fetch.source_problem(brief, read_urls)


def test_source_problem_none_when_enough_read_sources_cited(read_urls):
    urls = [f"https://site{i}.com/a" for i in range(REQUIRED_SOURCES)]
    read_urls.update(urls)
    brief = "## Sources\n" + "\n".join(f"[{i}] T - {u}" for i, u in enumerate(urls))
    assert fetch.source_problem(brief, read_urls) is None


def test_already_read_url_is_skipped_without_fetching(respond, read_urls):
    calls = respond(fake_response())
    read_urls.add("https://a.com/1")
    result = fetch.fetch_source("https://a.com/1", read_urls)
    assert result.outcome == "already_read"
    assert calls == []


def test_blocked_domain_is_skipped_without_fetching(respond, read_urls):
    calls = respond(fake_response())
    fetch.BLOCKED_DOMAINS.add("a.com")
    result = fetch.fetch_source("https://www.a.com/other", read_urls)
    assert result.outcome == "blocked_domain"
    assert calls == []
    assert "a.com blocks fetching" in fetch.format_fetch_result(result, read_urls)


@pytest.mark.parametrize("response, reason", [
    (None, "no response"),
    (fake_response(status=403), "HTTP 403"),
    (fake_response(status=202), "HTTP 202"),
])
def test_refused_fetch_blocks_the_domain(respond, response, reason, read_urls):
    respond(response)
    result = fetch.fetch_source("https://www.a.com/1", read_urls)
    assert result.outcome == "fetch_failed"
    assert result.reason == reason
    assert "a.com" in fetch.BLOCKED_DOMAINS
    assert f"Could not fetch https://www.a.com/1 ({reason})." in fetch.format_fetch_result(result, read_urls)


@pytest.mark.parametrize("status", [404, 410])
def test_missing_page_does_not_block_the_domain(respond, status, read_urls):
    respond(fake_response(status=status))
    result = fetch.fetch_source("https://a.com/gone", read_urls)
    assert result.outcome == "no_text"
    assert fetch.BLOCKED_DOMAINS == set()


def test_empty_extraction_is_no_text(respond, read_urls):
    respond(fake_response(), text=None)
    assert fetch.fetch_source("https://a.com/1", read_urls).outcome == "no_text"


def test_short_page_does_not_count_as_a_source(respond, read_urls):
    respond(fake_response(), text="x" * (MIN_SOURCE_CHARS - 1))
    result = fetch.fetch_source("https://a.com/1", read_urls)
    assert result.outcome == "too_short"
    assert read_urls == set()
    assert f"is too short ({MIN_SOURCE_CHARS - 1} chars)" in fetch.format_fetch_result(result, read_urls)


def test_good_page_is_recorded_and_returned(respond, read_urls):
    respond(fake_response())
    result = fetch.fetch_source("https://a.com/1", read_urls)
    assert result.outcome == "ok"
    assert read_urls == {"https://a.com/1"}
    message = fetch.format_fetch_result(result, read_urls)
    assert message.startswith(f"[Progress: 1 of {REQUIRED_SOURCES}")
    assert message.endswith(LONG_TEXT)


def test_tool_wiring_returns_text_for_a_good_page(respond, state):
    respond(fake_response())
    output = invoke_tool(fetch.fetch_and_extract, run_state=state, url="https://a.com/1")
    assert output.endswith(LONG_TEXT)
    assert state.read_urls == {"https://a.com/1"}


def test_tool_wiring_reports_a_refusal(respond, state):
    respond(fake_response(status=403))
    output = invoke_tool(fetch.fetch_and_extract, run_state=state, url="https://a.com/1")
    assert "Could not fetch https://a.com/1 (HTTP 403)." in output
    assert "do not try other pages on this site" in output


def test_tool_name_and_description_unchanged():
    assert fetch.fetch_and_extract.name == "fetch_and_extract"
    assert fetch.fetch_and_extract.description.startswith(
        "Fetch the content of a URL and extract its text using Trafilatura.")
