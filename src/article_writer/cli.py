"""Command line entry point: ``article-writer "topic"``."""

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

from article_writer import config


class IncompleteRunError(RuntimeError):
    """The run ended before a writer produced the article."""


def slugify(topic: str, max_length: int = 60) -> str:
    """Turn a topic into a safe file name stem."""
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:max_length].strip("_")
    return slug or "article"


_IMAGE_LINK = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)(\))")


def relink_images(article: str, out_dir: Path) -> str:
    """Rewrite image links so they resolve from the folder the article is saved in.

    The image tool returns paths relative to the current directory (e.g. output/images/x.jpg),
    which break once the article sits in another folder. Links to files that do not exist
    (and web URLs) are left alone.
    """
    def fix(match: re.Match) -> str:
        target = match.group(2)
        if "://" in target or not Path(target).is_file():
            return match.group(0)
        relative = Path(os.path.relpath(target, out_dir)).as_posix()
        return f"{match.group(1)}{relative}{match.group(3)}"

    return _IMAGE_LINK.sub(fix, article)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="article-writer",
        description="Research a topic, pick a writer, and produce a sourced article.",
    )
    parser.add_argument("topic", help="the topic to write about")
    parser.add_argument("--out", type=Path, default=config.OUTPUT_DIR, metavar="DIR",
                        help="directory for the article (default: %(default)s)")
    parser.add_argument("--max-turns", type=int, default=config.DEFAULT_MAX_TURNS,
                        help="turn limit for the orchestrator run (default: %(default)s)")
    parser.add_argument("--verbose", action="store_true", help="show progress messages")
    return parser


def setup_logging(verbose: bool) -> None:
    """Send article_writer log messages to stderr; progress (INFO) only when verbose."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("  %(message)s"))
    package_logger = logging.getLogger("article_writer")
    package_logger.handlers = [handler]
    package_logger.setLevel(logging.INFO if verbose else logging.WARNING)
    package_logger.propagate = False


async def write_article(topic: str, max_turns: int) -> tuple[str, str]:
    """Run the orchestrator on ``topic``. Returns (article markdown, name of the writer used)."""
    # Imported here so parsing arguments does not build the agents
    from agents import Runner, trace

    from article_writer.agents.orchestrator import orchestrator_agent

    with trace("Article Writer w/ styles", group_id="AIEP", metadata={"experimentID": "001"}):
        result = await Runner.run(orchestrator_agent, input=topic, max_turns=max_turns)
    # The orchestrator can end its turn with text instead of calling tools and handing off.
    # That leaves a stub, not an article, so fail instead of passing it off as one.
    if result.last_agent is orchestrator_agent:
        raise IncompleteRunError(
            "The orchestrator finished without handing off to a writer. "
            f"Its last message was: {str(result.final_output)[:200]!r}")
    return str(result.final_output), result.last_agent.name


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)
    try:
        config.require_api_key()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    try:
        article, writer = asyncio.run(write_article(args.topic, args.max_turns))
    except IncompleteRunError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{slugify(args.topic)}.md"
    path.write_text(relink_images(article, args.out), encoding="utf-8")
    print(f"Article: {path}")
    print(f"Writer: {writer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
