"""Run the source-breadth eval: ``python -m article_writer.evals.run_evals``.

Researches every topic in TOPICS and checks each brief two ways:
- the LLM judge (column ``failure``): does the brief cite at least 3 distinct sources?
- a code check (column ``check_failure``): does the brief have a Sources section that cites at
  least the required number of sources the agent actually read? ``check_detail`` holds the
  feedback when it does not.
For both columns TRUE means failed. The research step retries a brief that fails the check, so
``check_failure`` describes the final brief; ``first_attempt_failure`` is the same check on the
first brief, and ``attempts`` counts the tries. Results go to output/evals/<timestamp>.csv, and both
failure rates are printed.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from article_writer import config
from article_writer.agents.research import ResearchRun, run_research_checked
from article_writer.cli import setup_logging
from article_writer.evals.judge import judge
from article_writer.evals.topics import TOPICS

logger = logging.getLogger(__name__)

MAX_WORKERS = 5


async def run_research(topic: str, max_turns: int = config.RESEARCH_MAX_TURNS) -> ResearchRun:
    """Research ``topic`` the same way the orchestrator's research tool does."""
    return await run_research_checked(topic, max_turns=max_turns)


async def evaluate(topic: str, limit: asyncio.Semaphore) -> dict:
    """Research one topic, then judge and check the brief. Errors are recorded as "ERROR"."""
    async with limit:
        logger.info("[%d/%d] Researching: %s...", TOPICS.index(topic) + 1, len(TOPICS), topic[:60])
        try:
            run = await run_research(topic)
            # judge() is a blocking API call, so keep it off the event loop
            label = await asyncio.to_thread(judge, run.brief)
            return {"topic": topic, "failure": label, "brief": run.brief,
                    "check_failure": "TRUE" if run.problem else "FALSE",
                    "check_detail": run.problem or "",
                    "first_attempt_failure": "TRUE" if run.first_problem else "FALSE",
                    "attempts": run.attempts}
        except Exception as e:  # noqa: BLE001 (any failure becomes an ERROR row)
            return {"topic": topic, "failure": "ERROR", "brief": repr(e),
                    "check_failure": "ERROR", "check_detail": "",
                    "first_attempt_failure": "ERROR", "attempts": 0}


async def evaluate_all(topics: list[str], workers: int = MAX_WORKERS) -> list[dict]:
    """Evaluate every topic on one event loop, at most ``workers`` at a time, in topic order.

    One loop matters: the SDK's shared HTTP client cannot be used across several loops.
    """
    limit = asyncio.Semaphore(workers)
    return list(await asyncio.gather(*(evaluate(t, limit) for t in topics)))


def failure_rate(df: pd.DataFrame, column: str = "failure") -> float | None:
    """Share of scored runs (TRUE or FALSE) in ``column`` that failed, or None if none scored."""
    scored = df[column].isin(["TRUE", "FALSE"]).sum()
    return (df[column] == "TRUE").sum() / scored if scored else None


def _percent(rate: float | None) -> str:
    return "n/a" if rate is None else f"{rate:.0%}"


def main() -> int:
    setup_logging(verbose=True)
    try:
        config.require_api_key()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    df = pd.DataFrame(asyncio.run(evaluate_all(TOPICS)))

    out_dir = Path(config.EVAL_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{datetime.now():%Y%m%d_%H%M%S}.csv"
    df.to_csv(path, index=False)

    print("LLM judge labels:\n" + df["failure"].value_counts().to_string(), "\n")
    print("Source check labels:\n" + df["check_failure"].value_counts().to_string(), "\n")
    print(f"Failure rate, LLM judge (scored runs): {_percent(failure_rate(df))}")
    print(f"Failure rate, source check, first attempt: "
          f"{_percent(failure_rate(df, 'first_attempt_failure'))}")
    print(f"Failure rate, source check, after retries: {_percent(failure_rate(df, 'check_failure'))}")
    print(f"Results: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
