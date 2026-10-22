from langchain_core.messages import AIMessage

from app.agents.cold_search import RepositoryTools, cold_search
from app.models.answer import AnswerResult
from app.services.citation_validator import validate_source_citations
from app.services.repositories import REPO_ROOT


class ScriptedToolModel:
    """Returns the scripted replies in order, then stops calling tools."""

    def __init__(self, *tool_calls):
        self.replies = [
            AIMessage(content="", tool_calls=[{**call, "id": str(i)}])
            for i, call in enumerate(tool_calls)
        ]
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.replies:
            return self.replies.pop(0)
        return AIMessage(content="Done.")


def test_agent_collects_read_spans_as_evidence():
    model = ScriptedToolModel(
        {"name": "grep", "args": {"pattern": "def require_user", "path": "."}},
        {
            "name": "read_file",
            "args": {"path": "src/auth.py", "start_line": 4, "end_line": 8},
        },
    )

    result = cold_search("Where is authentication implemented?", REPO_ROOT, model)

    assert result.tool_calls == 2
    assert model.calls == 3
    assert [(c.path, c.start_line, c.end_line) for c in result.citations] == [
        ("src/auth.py", 4, 8)
    ]
    # Evidence comes straight from the file, so it passes citation checks.
    validated = validate_source_citations(
        AnswerResult(answer="x", citations=result.citations, status="answered")
    )
    assert validated.status == "answered"


def test_agent_stops_at_step_budget():
    class AlwaysSearching:
        def invoke(self, messages):
            return AIMessage(
                content="",
                tool_calls=[{"name": "list_dir", "args": {"path": "."}, "id": "loop"}],
            )

    result = cold_search("anything", REPO_ROOT, AlwaysSearching(), max_steps=3)

    assert result.tool_calls == 3
    assert result.citations == []


def test_tools_stay_inside_repository():
    tools = RepositoryTools(REPO_ROOT)

    assert tools.list_dir("..").startswith("Error")
    assert tools.read_file("../../pyproject.toml", 1, 5).startswith("Error")
    assert tools.call("delete_everything", {}).startswith("Error")
    assert tools.evidence == []


def test_grep_and_read_file_output():
    tools = RepositoryTools(REPO_ROOT)

    assert "src/auth.py:7:" in tools.grep("PermissionError", ".")
    assert "src/" in tools.list_dir(".")
    # Out-of-range end lines are clamped to the file length.
    assert tools.read_file("src/auth.py", 7, 500).splitlines()[-1].startswith("    8|")
