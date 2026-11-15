"""Research agent: searches the web, reads sources, and writes a cited brief."""

import logging
from dataclasses import dataclass

from agents import Agent, Runner, function_tool

from article_writer.config import (
    MODEL,
    REQUIRED_SOURCES,
    RESEARCH_MAX_RETRIES,
    RESEARCH_MAX_TURNS,
)
from article_writer.models import ResearchState
from article_writer.prompts import render
from article_writer.tools.fetch import fetch_and_extract, source_problem
from article_writer.tools.search import search_web

logger = logging.getLogger(__name__)

research_agent = Agent(
    name="research_agent",
    instructions=render("research"),
    model=MODEL,
    tools=[search_web, fetch_and_extract],
)

RESEARCH_TOOL_DESCRIPTION = (
    "Researches a topic and returns a research brief in Markdown. "
    "Give it a topic or question as input. It plans the key angles, searches the web, "
    f"reads the full text of {REQUIRED_SOURCES} distinct sources, and checks for gaps before writing. "
    "The brief contains a title, Summary, Key Findings (with key facts, statistics and "
    "data points), Conclusion (including limitations), and a numbered Sources list with "
    "URLs, with inline [n] citations. Only facts found in the sources it read are included. "
    "Each call is independent and quality can vary, so results can differ between calls."
)


@dataclass
class ResearchRun:
    """The outcome of researching one topic, including how many tries it took."""

    brief: str
    read_urls: set[str]
    attempts: int
    first_problem: str | None  # what was wrong with the first brief, None if it was fine
    problem: str | None  # what is still wrong with the final brief, None if it passes


async def run_research_checked(
    topic: str,
    max_turns: int = RESEARCH_MAX_TURNS,
    max_retries: int = RESEARCH_MAX_RETRIES,
) -> ResearchRun:
    """Run the research agent and check its brief with source_problem.

    The agent sometimes ends a turn with a progress note instead of the report. When the brief
    fails the check, the conversation continues with the check's feedback (up to ``max_retries``
    times). All attempts share one ResearchState, so sources already read still count.
    """
    state = ResearchState()
    agent_input: str | list = topic
    first_problem = None
    for attempt in range(1, max_retries + 2):
        result = await Runner.run(
            research_agent, input=agent_input, context=state, max_turns=max_turns)
        brief = str(result.final_output)
        problem = source_problem(brief, state.read_urls)
        if attempt == 1:
            first_problem = problem
        if problem is None or attempt == max_retries + 1:
            return ResearchRun(brief, state.read_urls, attempt, first_problem, problem)
        logger.info("\N{WARNING SIGN} Brief failed the source check (attempt %d). Asking for a rewrite.",
                    attempt)
        agent_input = [*result.to_input_list(), {"role": "user", "content": problem}]
    raise AssertionError("unreachable")


@function_tool(name_override="research_agent", description_override=RESEARCH_TOOL_DESCRIPTION)
async def research_agent_as_tool(input: str) -> str:
    """Run the research agent on ``input`` with its own ResearchState.

    Agent.as_tool() would share the caller's run context, and with it one set of read sources,
    across both research calls. Running the agent here gives every call a fresh state, and a
    brief that fails the source check is retried instead of being handed on as a stub.
    """
    run = await run_research_checked(input)
    if run.problem:
        return f"Research failed after {run.attempts} attempts. {run.problem}"
    return run.brief
