"""Models, limits, and paths. Every value can be overridden with an environment variable.

Importing this module loads ``.env`` (searching upward from the current directory).
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

load_dotenv(find_dotenv(usecwd=True))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


# Models
MODEL = os.getenv("ARTICLE_WRITER_MODEL", "gpt-4.1-mini")
JUDGE_MODEL = os.getenv("ARTICLE_WRITER_JUDGE_MODEL", "gpt-5-mini")
IMAGE_MODEL = os.getenv("ARTICLE_WRITER_IMAGE_MODEL", "gpt-image-2.5-flare")

# Research limits
REQUIRED_SOURCES = _int("ARTICLE_WRITER_REQUIRED_SOURCES", 4)  # sources the researcher reads, then stops
MIN_SOURCE_CHARS = _int("ARTICLE_WRITER_MIN_SOURCE_CHARS", 2000)  # shorter pages don't count
NUM_RESULTS = _int("ARTICLE_WRITER_NUM_RESULTS", 10)
MAX_PAGES = _int("ARTICLE_WRITER_MAX_PAGES", 3)
MIN_SEARCH_INTERVAL = _float("ARTICLE_WRITER_MIN_SEARCH_INTERVAL", 2.5)  # seconds between searches
FETCH_TIMEOUT = _int("ARTICLE_WRITER_FETCH_TIMEOUT", 10)  # seconds

# Run limits
DEFAULT_MAX_TURNS = _int("ARTICLE_WRITER_MAX_TURNS", 30)
RESEARCH_MAX_TURNS = _int("ARTICLE_WRITER_RESEARCH_MAX_TURNS", 25)

# Paths (relative paths resolve against the current directory)
OUTPUT_DIR = Path(os.getenv("ARTICLE_WRITER_OUTPUT_DIR", "output"))
IMAGE_DIR = Path(os.getenv("ARTICLE_WRITER_IMAGE_DIR", str(OUTPUT_DIR / "images")))
EVAL_DIR = Path(os.getenv("ARTICLE_WRITER_EVAL_DIR", str(OUTPUT_DIR / "evals")))


def require_api_key() -> str:
    """Return OPENAI_API_KEY, or raise if it is not set."""
    key = os.getenv("OPENAI_API_KEY")
    if key is None:
        raise RuntimeError("API Key is missing: set OPENAI_API_KEY in the environment or in .env")
    return key


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Return the shared OpenAI client, created on first use so imports need no key."""
    return OpenAI(api_key=require_api_key())
