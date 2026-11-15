"""Run the source-breadth eval: ``python -m article_writer.evals.run_evals``.

Researches every topic in TOPICS, judges each brief, writes output/evals/<timestamp>.csv,
and prints the failure rate.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from article_writer import config
from article_writer.cli import setup_logging
from article_writer.evals.judge import judge
from article_writer.evals.topics import TOPICS

logger = logging.getLogger(__name__)

MAX_WORKERS = 5


async def run_research(topic: str, max_turns: int = config.RESEARCH_MAX_TURNS) -> str:
    """Run the research agent on ``topic`` and return its brief."""
    from agents import Runner

    from article_writer.agents.research import research_agent
    from article_writer.models import ResearchState

    result = await Runner.run(
        research_agent, input=topic, context=ResearchState(), max_turns=max_turns)
    return str(result.final_output)


async def evaluate(topic: str, limit: asyncio.Semaphore) -> dict:
    """Research one topic and judge the brief. Errors are recorded as the label "ERROR"."""
    async with limit:
        logger.info("[%d/%d] Researching: %s...", TOPICS.index(topic) + 1, len(TOPICS), topic[:60])
        try:
            brief = await run_research(topic)
            # judge() is a blocking API call, so keep it off the event loop
            label = await asyncio.to_thread(judge, brief)
            return {"topic": topic, "failure": label, "brief": brief}
        except Exception as e:  # noqa: BLE001 (any failure becomes an ERROR row)
            return {"topic": topic, "failure": "ERROR", "brief": repr(e)}


async def evaluate_all(topics: list[str], workers: int = MAX_WORKERS) -> list[dict]:
    """Evaluate every topic on one event loop, at most ``workers`` at a time, in topic order.

    One loop matters: the SDK's shared HTTP client cannot be used across several loops.
    """
    limit = asyncio.Semaphore(workers)
    return list(await asyncio.gather(*(evaluate(t, limit) for t in topics)))


def failure_rate(df: pd.DataFrame) -> float | None:
    """Share of scored runs (TRUE or FALSE) that failed, or None if no run was scored."""
    scored = df["failure"].isin(["TRUE", "FALSE"]).sum()
    return (df["failure"] == "TRUE").sum() / scored if scored else None


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

    print(df["failure"].value_counts().to_string(), "\n")
    rate = failure_rate(df)
    print(f"Failure rate (scored runs): {'n/a' if rate is None else f'{rate:.0%}'}")
    print(f"Results: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
