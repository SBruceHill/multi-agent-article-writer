from types import SimpleNamespace

from conftest import invoke_tool

from article_writer.agents import research
from article_writer.config import REQUIRED_SOURCES
from article_writer.models import ResearchState


def test_tool_keeps_the_name_description_and_input_schema():
    tool = research.research_agent_as_tool
    assert tool.name == "research_agent"
    assert tool.description.startswith("Researches a topic and returns a research brief in Markdown.")
    assert f"reads the full text of {REQUIRED_SOURCES} distinct sources" in tool.description
    assert list(tool.params_json_schema["properties"]) == ["input"]


def test_each_research_call_gets_its_own_state(monkeypatch):
    seen = []

    async def fake_run(agent, input, context, max_turns):
        seen.append((agent, input, context, max_turns))
        context.read_urls.add(f"https://example.com/{len(seen)}")
        return SimpleNamespace(final_output=f"brief {len(seen)}")

    monkeypatch.setattr(research.Runner, "run", fake_run)
    first = invoke_tool(research.research_agent_as_tool, input="topic one")
    second = invoke_tool(research.research_agent_as_tool, input="topic two")

    assert (first, second) == ("brief 1", "brief 2")
    (_, _, state_1, turns), (_, _, state_2, _) = seen
    assert isinstance(state_1, ResearchState) and state_1 is not state_2
    assert state_1.read_urls == {"https://example.com/1"}
    assert state_2.read_urls == {"https://example.com/2"}
    assert turns == research.RESEARCH_MAX_TURNS
