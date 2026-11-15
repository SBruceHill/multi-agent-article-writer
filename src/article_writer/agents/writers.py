"""Writer agents. The orchestrator hands off to exactly one of them."""

from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from article_writer.config import MODEL
from article_writer.prompts import render

journalist_agent = Agent(
    name="journalist_agent",
    instructions=RECOMMENDED_PROMPT_PREFIX + render("journalist"),
    model=MODEL,
)

storyteller_agent = Agent(
    name="storyteller_agent",
    instructions=RECOMMENDED_PROMPT_PREFIX + render("storyteller"),
    model=MODEL,
)
