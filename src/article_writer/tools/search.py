"""Web search through DuckDuckGo, throttled and retried."""

import json
import logging
import threading
import time
from dataclasses import dataclass

from agents import function_tool
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from article_writer.config import MAX_PAGES, MIN_SEARCH_INTERVAL, NUM_RESULTS
from article_writer.tools.fetch import BLOCKED_DOMAINS, domain_of

logger = logging.getLogger(__name__)

ddgs = DDGS()

_search_lock = threading.Lock()
_last_search_time = 0.0


def throttled_text(query: str, page: int):
    """Run one DuckDuckGo request at a time, spaced out, so parallel tool calls don't trigger rate limits."""
    global _last_search_time
    with _search_lock:
        wait = MIN_SEARCH_INTERVAL - (time.monotonic() - _last_search_time)
        if wait > 0:
            time.sleep(wait)
        try:
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
