"""Web search through Brave (when a key is set) or DuckDuckGo, throttled and retried."""

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass

import requests
from agents import function_tool
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from article_writer.config import (
    BRAVE_MIN_INTERVAL,
    MAX_PAGES,
    MIN_SEARCH_INTERVAL,
    NUM_RESULTS,
    SEARCH_PROVIDER,
)
from article_writer.tools.fetch import BLOCKED_DOMAINS, domain_of

logger = logging.getLogger(__name__)

ddgs = DDGS()

_search_lock = threading.Lock()
_last_search_time = 0.0


BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
_TAGS = re.compile(r"<[^>]+>")


class BraveError(Exception):
    """A Brave Search request failed (network error, bad key, rate limit, or bad response)."""


def use_brave() -> bool:
    """True if Brave should serve searches: forced by config, or auto with a key present."""
    if SEARCH_PROVIDER == "ddgs":
        return False
    return bool(os.getenv("BRAVE_API_KEY")) or SEARCH_PROVIDER == "brave"


def brave_text(query: str, page: int) -> list[dict]:
    """Fetch one page of Brave web results as {title, href, body} dicts (the shape ddgs uses).

    Raises BraveError on any failure.
    """
    key = os.getenv("BRAVE_API_KEY")
    if not key:
        raise BraveError("BRAVE_API_KEY is not set")
    try:
        response = requests.get(
            BRAVE_URL,
            headers={"Accept": "application/json", "X-Subscription-Token": key},
            params={"q": query, "count": NUM_RESULTS, "offset": page - 1},
            timeout=15,
        )
        if response.status_code != 200:
            raise BraveError(f"HTTP {response.status_code}")
        items = response.json().get("web", {}).get("results", [])
    except (requests.RequestException, ValueError) as e:
        raise BraveError(str(e)) from e
    return [
        {"title": item.get("title", ""), "href": item.get("url", ""),
         "body": _TAGS.sub("", item.get("description", ""))}
        for item in items
    ]


def throttled_text(query: str, page: int):
    """Run one search request at a time, spaced out, so parallel tool calls don't trigger rate limits.

    Uses Brave when configured and falls back to DuckDuckGo if the Brave request fails.
    """
    global _last_search_time
    with _search_lock:
        brave = use_brave()
        interval = BRAVE_MIN_INTERVAL if brave else MIN_SEARCH_INTERVAL
        wait = interval - (time.monotonic() - _last_search_time)
        if wait > 0:
            time.sleep(wait)
        if page == 1:
            logger.info("Searching with %s: %s", "Brave" if brave else "DuckDuckGo", query)
        try:
            if brave:
                try:
                    return brave_text(query, page)
                except BraveError as e:
                    logger.warning("\N{WARNING SIGN} Brave search failed (%s). Using DuckDuckGo.", e)
                    time.sleep(max(0, MIN_SEARCH_INTERVAL - BRAVE_MIN_INTERVAL))
            return ddgs.text(query, max_results=NUM_RESULTS, page=page)
        finally:
            _last_search_time = time.monotonic()


@dataclass
class SearchOutcome:
    """The best result set found for a query, and the last error if it came up short."""

    results: list[dict]
    error: object | None  # the last error (an exception or message), None if nothing went wrong
    retries: int


def search_with_backoff(query: str, retries: int = 3, delay: float = 2) -> SearchOutcome:
    """Search for ``query``, retrying with exponential backoff until NUM_RESULTS results are found.

    Keeps the largest result set seen across attempts, even if a later page failed.
    """
    best: list[dict] = []
    error = None
    for attempt in range(1, retries + 1):
        results, seen, error = [], set(), None
        # ddgs wraps all engine failures (including rate limits) in DDGSException;
        # TimeoutException is a subclass, so this catches both
        try:
            # A single page often returns fewer than max_results, so keep paging until we have enough
            for page in range(1, MAX_PAGES + 1):
                batch = throttled_text(query, page)
                if not batch:
                    break
                for result in batch:
                    href = result.get("href", "")
                    if href and href not in seen:
                        seen.add(href)
                        results.append(result)
                if len(results) >= NUM_RESULTS:
                    break
        except DDGSException as e:
            error = e

        results = results[:NUM_RESULTS]
        if len(results) > len(best):
            best = results
        if len(best) == NUM_RESULTS:
            break
        if error is None:
            error = f"Only {len(best)} results found." if best else "No results found."

        if attempt < retries:
            logger.info("\N{WARNING SIGN} Search incomplete (%s). Retrying in %ss...", error, delay)
            time.sleep(delay)
            delay *= 2
    return SearchOutcome(best, error, retries)


@function_tool
def search_web(query: str):
    """Search the web with DuckDuckGo and return 10 results, retrying with exponential backoff."""
    outcome = search_with_backoff(query)
    if outcome.results:
        # Flag results from sites that already blocked a fetch in this run
        for result in outcome.results:
            if domain_of(result.get("href", "")) in BLOCKED_DOMAINS:
                result["fetchable"] = False
        logger.info("\N{WHITE HEAVY CHECK MARK} Got %d results for %s", len(outcome.results), query)
        return json.dumps(outcome.results, indent=2)

    logger.info("\N{CROSS MARK} Search failed after %d attempts: %s", outcome.retries, outcome.error)
    return f"Search for '{query}' failed ({outcome.error}). Try a different or broader query."
