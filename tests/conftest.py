import asyncio
import json

import pytest
from agents.tool_context import ToolContext

from article_writer.models import ResearchState
from article_writer.tools import fetch


@pytest.fixture(autouse=True)
def no_live_search(monkeypatch):
    """Keep a real BRAVE_API_KEY from .env out of tests."""
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def clean_run_state():
    """Start every test with no blocked domains."""
    fetch.BLOCKED_DOMAINS.clear()
    yield
    fetch.BLOCKED_DOMAINS.clear()


@pytest.fixture
def state() -> ResearchState:
    """A fresh research run state (the set of sources read so far)."""
    return ResearchState()


@pytest.fixture
def read_urls(state) -> set[str]:
    return state.read_urls


def invoke_tool(tool, *, run_state=None, **arguments) -> str:
    """Call a @function_tool the way the SDK does, through FunctionTool.on_invoke_tool."""
    ctx = ToolContext(context=run_state, tool_name=tool.name, tool_call_id="call_1",
                      tool_arguments=json.dumps(arguments))
    return asyncio.run(tool.on_invoke_tool(ctx, json.dumps(arguments)))
