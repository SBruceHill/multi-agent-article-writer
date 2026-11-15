import asyncio
import json

import pytest
from agents.tool_context import ToolContext

from article_writer.tools import fetch


@pytest.fixture(autouse=True)
def clean_run_state():
    """Start every test with no sources read and no blocked domains."""
    fetch.READ_URLS.clear()
    fetch.BLOCKED_DOMAINS.clear()
    yield
    fetch.READ_URLS.clear()
    fetch.BLOCKED_DOMAINS.clear()


def invoke_tool(tool, **arguments) -> str:
    """Call a @function_tool the way the SDK does, through FunctionTool.on_invoke_tool."""
    ctx = ToolContext(context=None, tool_name=tool.name, tool_call_id="call_1",
                      tool_arguments=json.dumps(arguments))
    return asyncio.run(tool.on_invoke_tool(ctx, json.dumps(arguments)))
