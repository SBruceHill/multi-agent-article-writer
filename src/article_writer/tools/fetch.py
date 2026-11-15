"""Page fetching and source bookkeeping (BLOCKED_DOMAINS here, read URLs in ResearchState)."""

import logging
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import trafilatura
from agents import RunContextWrapper, function_tool
from trafilatura.downloads import fetch_response
from trafilatura.settings import use_config

from article_writer.config import FETCH_TIMEOUT, MIN_SOURCE_CHARS, REQUIRED_SOURCES
from article_writer.models import ResearchState

logger = logging.getLogger(__name__)

# Domains that refused a fetch. Deliberately module level: it is a per-domain cache of
# sites that refuse fetches, shared by every research run in this process.
BLOCKED_DOMAINS: set[str] = set()

# Statuses that mean only this page is missing, not that the site is blocking us
PAGE_ONLY_STATUSES = {404, 410}

# trafilatura defaults to a 30s timeout, and its retry backoff is half the timeout,
# so one unresponsive site can stall the agent for minutes. A short timeout keeps failures fast.
FETCH_CONFIG = use_config()
FETCH_CONFIG["DEFAULT"]["DOWNLOAD_TIMEOUT"] = str(FETCH_TIMEOUT)


def domain_of(url: str) -> str:
    """Return the URL's domain, lowercased and without a leading 'www.'."""
    return urlparse(url).netloc.lower().removeprefix("www.")


def source_progress(read_urls: set[str]) -> str:
    """Tell the agent how many sources it has read so far against the required minimum."""
    read, remaining = len(read_urls), REQUIRED_SOURCES - len(read_urls)
    if remaining > 0:
        return (f"[Progress: {read} of {REQUIRED_SOURCES} required sources read successfully. "
                f"Read at least {remaining} more before writing the report.]")
    return (f"[Progress: {read} of {REQUIRED_SOURCES} required sources read successfully. The requirement is met: "
            f"STOP searching and reading, and write the report now. "
            f"Cite only these sources: {', '.join(sorted(read_urls))}]")


def normalize_url(url: str) -> str:
    """Reduce a URL to domain + path + query so trivial differences (www, trailing slash) still match."""
    parts = urlparse(url.strip().rstrip(".,;"))
    query = f"?{parts.query}" if parts.query else ""
    return f"{domain_of(url)}{parts.path.rstrip('/')}{query}".lower()


def source_problem(brief: str, read_urls: set[str]) -> str | None:
    """Return feedback if the brief's Sources list cites unread or too few read sources, else None."""
    if "## Sources" not in brief:
        return ("Your reply is not a complete brief: it has no '## Sources' section. Reply with only "
                "the complete brief in the required format, with no preface.")
    sources = brief.split("## Sources", 1)[1]
    cited = {normalize_url(u) for u in re.findall(r"https?://[^\s)\]>]+", sources)}
    read = {normalize_url(u) for u in read_urls}
    unread, cited_read = sorted(cited - read), cited & read
    problems = []
    if unread:
        problems.append("It cites sources you did not read successfully with fetch_and_extract: "
                        + ", ".join(unread) + ". Read them or remove them.")
    if len(cited_read) < REQUIRED_SOURCES:
        problems.append(f"It cites only {len(cited_read)} sources you have read, but at least "
                        f"{REQUIRED_SOURCES} are required. Read more sources with fetch_and_extract.")
    if not problems:
        return None
    return ("Your brief does not meet the source requirement. " + " ".join(problems)
            + " Then reply with only the complete rewritten brief in the required format, with no preface.")


FetchOutcome = Literal["ok", "already_read", "blocked_domain", "fetch_failed", "no_text", "too_short"]


@dataclass
class FetchResult:
    """What happened when we tried to read a URL as a source."""

    outcome: FetchOutcome
    url: str
    domain: str
    text: str = ""
    reason: str = ""  # only set for "fetch_failed": "no response" or "HTTP <status>"


def fetch_source(url: str, read_urls: set[str]) -> FetchResult:
    """Decide whether ``url`` can be read and, if so, fetch and extract its text.

    Updates ``read_urls`` (this run's sources) on success and BLOCKED_DOMAINS when the site refuses the fetch.
    """
    domain = domain_of(url)
    if url in read_urls:
        logger.info("\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} Already read %s.", url)
        return FetchResult("already_read", url, domain)

    if domain in BLOCKED_DOMAINS:
        logger.info("\N{NO ENTRY SIGN} Skipped %s: blocked earlier in this run.", domain)
        return FetchResult("blocked_domain", url, domain)

    response = fetch_response(url, decode=True, config=FETCH_CONFIG)

    # No response (timeout, refused or reset connection) or an unexpected status such as
    # 403 or a 202 bot challenge means the site is refusing us, so its other pages will fail too
    if response is None or (response.status != 200 and response.status not in PAGE_ONLY_STATUSES):
        BLOCKED_DOMAINS.add(domain)
        reason = "no response" if response is None else f"HTTP {response.status}"
        logger.info("\N{CROSS MARK} %s blocked the fetch (%s).", domain, reason)
        return FetchResult("fetch_failed", url, domain, reason=reason)

    text = trafilatura.extract(response.html) if response.status == 200 else None
    if not text:
        logger.info("\N{CROSS MARK} Failed to get text from URL.")
        return FetchResult("no_text", url, domain)

    if len(text) < MIN_SOURCE_CHARS:
        logger.info("\N{CROSS MARK} Too short (%d chars): %s", len(text), url[:60])
        return FetchResult("too_short", url, domain, text=text)

    read_urls.add(url)
    logger.info("\N{WHITE HEAVY CHECK MARK} fetch_and_extract: got %d chars from %s (%d/%d sources read)",
                len(text), url[:60], len(read_urls), REQUIRED_SOURCES)
    return FetchResult("ok", url, domain, text=text)


def format_fetch_result(result: FetchResult, read_urls: set[str]) -> str:
    """Build the message the agent sees for a fetch result."""
    url, domain = result.url, result.domain
    match result.outcome:
        case "already_read":
            return f"You already read {url}. Choose a different source.\n{source_progress(read_urls)}"
        case "blocked_domain":
            return (f"Skipped {url}: {domain} blocks fetching. Choose a source from a different site.\n"
                    f"{source_progress(read_urls)}")
        case "fetch_failed":
            return (f"Could not fetch {url} ({result.reason}). {domain} blocks fetching, so do not try other "
                    f"pages on this site. Choose a source from a different site.\n{source_progress(read_urls)}")
        case "no_text":
            return f"Could not fetch and extract text from {url}. Try a different source.\n{source_progress(read_urls)}"
        case "too_short":
            return (f"{url} is too short ({len(result.text)} chars) to count as a source. "
                    f"Choose a longer, more substantive article.\n{source_progress(read_urls)}")
        case _:
            return f"{source_progress(read_urls)}\n\n{result.text}"


@function_tool
def fetch_and_extract(ctx: RunContextWrapper[ResearchState], url: str):
    """Fetch the content of a URL and extract its text using Trafilatura.

    Domains that refuse a fetch are added to BLOCKED_DOMAINS and skipped for the rest of the run.
    """
    read_urls = ctx.context.read_urls
    return format_fetch_result(fetch_source(url, read_urls), read_urls)
