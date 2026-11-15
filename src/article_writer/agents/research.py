"""Research agent: searches the web, reads sources, and writes a cited brief."""

from agents import Agent

from article_writer.config import MODEL, REQUIRED_SOURCES, RESEARCH_MAX_TURNS
from article_writer.prompts import render
from article_writer.tools.fetch import fetch_and_extract
from article_writer.tools.search import search_web

research_agent = Agent(
    name="research_agent",
    instructions=render("research"),
    model=MODEL,
    tools=[search_web, fetch_and_extract],
)

research_agent_as_tool = research_agent.as_tool(
    tool_name="research_agent",
    tool_description=(
        "Researches a topic and returns a research brief in Markdown. "
        "Give it a topic or question as input. It plans the key angles, searches the web, "
        f"reads the full text of {REQUIRED_SOURCES} distinct sources, and checks for gaps before writing. "
        "The brief contains a title, Summary, Key Findings (with key facts, statistics and "
        "data points), Conclusion (including limitations), and a numbered Sources list with "
        "URLs, with inline [n] citations. Only facts found in the sources it read are included. "
        "Each call is independent and quality can vary, so results can differ between calls."
    ),
    max_turns=RESEARCH_MAX_TURNS,
)
