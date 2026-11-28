from types import SimpleNamespace
from uuid import uuid4

from google.genai import types

from app.agents.gemini_agent import GeminiAgent
from app.repositories.conversation_repository import ConversationRepository
from app.services.llm_provider import llm_provider


def make_response(text: str):
    content = types.Content(
        role="model",
        parts=[types.Part(text=text)],
    )

    return SimpleNamespace(
        candidates=[SimpleNamespace(content=content)],
        text=text,
    )


def test_conversation_history_is_restored_between_requests(monkeypatch):
    conversation_id = uuid4()
    db = object()

    stored_messages = []
    captured_contents = []

    def get_messages(db, conversation_id):
        return list(stored_messages)

    def add_message(
        db,
        conversation_id,
        role,
        content=None,
        gemini_payload=None,
    ):
        stored_messages.append(
            SimpleNamespace(
                role=role,
                content=content,
                gemini_payload=gemini_payload,
            )
        )

    def generate_content(contents, config):
        captured_contents.append(list(contents))

        if len(captured_contents) == 1:
            return make_response("I found some Python jobs.")

        return make_response("Here are more details.")

    monkeypatch.setattr(
        ConversationRepository,
        "get_messages",
        staticmethod(get_messages),
    )

    monkeypatch.setattr(
        ConversationRepository,
        "add_message",
        staticmethod(add_message),
    )

    monkeypatch.setattr(
        GeminiAgent,
        "_build_config",
        classmethod(lambda cls: object()),
    )

    monkeypatch.setattr(
        llm_provider,
        "generate_content",
        generate_content,
    )

    first_result = GeminiAgent.run(
        message="Find Python backend jobs.",
        profile_id=1,
        db=db,
        conversation_id=conversation_id,
    )

    assert first_result["message"] == "I found some Python jobs."
    assert len(stored_messages) == 2

    second_result = GeminiAgent.run(
        message="Tell me more about them.",
        profile_id=1,
        db=db,
        conversation_id=conversation_id,
    )

    assert second_result["message"] == "Here are more details."

    second_request_contents = captured_contents[1]

    assert len(second_request_contents) == 3

    assert second_request_contents[0].parts[0].text == (
        "Find Python backend jobs."
    )

    assert second_request_contents[1].parts[0].text == (
        "I found some Python jobs."
    )

    assert second_request_contents[2].parts[0].text == (
        "Tell me more about them."
    )

    assert len(stored_messages) == 4


def test_function_call_payload_round_trip():
    original = types.Content(
        role="model",
        parts=[
            types.Part(
                function_call=types.FunctionCall(
                    id="call-test-001",
                    name="search_jobs",
                    args={"keyword": "Python Backend Engineer"},
                )
            )
        ],
    )

    payload = GeminiAgent._serialize_content(original)
    restored = types.Content.model_validate(payload)

    function_call = restored.parts[0].function_call

    assert restored.role == "model"
    assert function_call.id == "call-test-001"
    assert function_call.name == "search_jobs"
    assert function_call.args == {
        "keyword": "Python Backend Engineer"
    }


def test_function_response_is_restored_between_requests(monkeypatch):
    from app.agents.tool_registry import ToolRegistry
    from app.schemas.agent import AgentToolResult

    conversation_id = uuid4()
    db = object()

    stored_messages = []
    captured_contents = []
    call_count = 0

    def get_messages(db, conversation_id):
        return list(stored_messages)

    def add_message(
        db,
        conversation_id,
        role,
        content=None,
        gemini_payload=None,
    ):
        stored_messages.append(
            SimpleNamespace(
                role=role,
                content=content,
                gemini_payload=gemini_payload,
            )
        )

    def execute(name, arguments, db, profile_id):
        return AgentToolResult(
            name=name,
            success=True,
            result={"total": 3},
        )

    def generate_content(contents, config):
        nonlocal call_count
        call_count += 1
        captured_contents.append(list(contents))

        if call_count == 1:
            content = types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="call-memory-001",
                            name="search_jobs",
                            args={"keyword": "Python"},
                        )
                    )
                ],
            )

            return SimpleNamespace(
                candidates=[SimpleNamespace(content=content)],
                text=None,
            )

        if call_count == 2:
            return make_response("I found three jobs.")

        return make_response("The tool history was restored.")

    monkeypatch.setattr(
        ConversationRepository,
        "get_messages",
        staticmethod(get_messages),
    )
    monkeypatch.setattr(
        ConversationRepository,
        "add_message",
        staticmethod(add_message),
    )
    monkeypatch.setattr(
        GeminiAgent,
        "_build_config",
        classmethod(lambda cls: object()),
    )
    monkeypatch.setattr(
        ToolRegistry,
        "execute",
        staticmethod(execute),
    )
    monkeypatch.setattr(
        llm_provider,
        "generate_content",
        generate_content,
    )

    first_result = GeminiAgent.run(
        message="Search Python jobs.",
        profile_id=1,
        db=db,
        conversation_id=conversation_id,
    )

    assert first_result["message"] == "I found three jobs."
    assert len(first_result["tool_calls"]) == 1
    assert len(first_result["tool_results"]) == 1
    assert len(stored_messages) == 4

    second_result = GeminiAgent.run(
        message="Tell me more.",
        profile_id=1,
        db=db,
        conversation_id=conversation_id,
    )

    assert second_result["message"] == "The tool history was restored."

    restored_contents = captured_contents[2]

    assert len(restored_contents) == 5

    restored_call = restored_contents[1].parts[0].function_call
    assert restored_call.id == "call-memory-001"
    assert restored_call.name == "search_jobs"

    restored_response = restored_contents[2].parts[0].function_response
    assert restored_response.id == "call-memory-001"
    assert restored_response.name == "search_jobs"
    assert restored_response.response["success"] is True
    assert restored_response.response["result"] == {"total": 3}

    assert restored_contents[4].parts[0].text == "Tell me more."


def test_agent_generates_final_summary_after_max_tool_rounds(monkeypatch):
    from app.agents.tool_registry import ToolRegistry
    from app.schemas.agent import AgentToolResult

    conversation_id = uuid4()
    db = object()

    stored_messages = []
    config_calls = []
    generate_calls = []

    def get_messages(db, conversation_id):
        return list(stored_messages)

    def add_message(
        db,
        conversation_id,
        role,
        content=None,
        gemini_payload=None,
    ):
        stored_messages.append(
            SimpleNamespace(
                role=role,
                content=content,
                gemini_payload=gemini_payload,
            )
        )

    def build_config(cls, enable_tools=True):
        config = {"enable_tools": enable_tools}
        config_calls.append(config)
        return config

    def execute(name, arguments, db, profile_id):
        return AgentToolResult(
            name=name,
            success=True,
            result={"executed": True},
        )

    def generate_content(contents, config):
        generate_calls.append(config)

        call_number = len(generate_calls)

        if call_number <= GeminiAgent.MAX_TOOL_ROUNDS:
            content = types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id=f"call-round-{call_number}",
                            name="search_jobs",
                            args={"keyword": "Python"},
                        )
                    )
                ],
            )

            return SimpleNamespace(
                candidates=[SimpleNamespace(content=content)],
                text=None,
            )

        return make_response(
            "I completed all five tool rounds and summarized the results."
        )

    monkeypatch.setattr(
        ConversationRepository,
        "get_messages",
        staticmethod(get_messages),
    )
    monkeypatch.setattr(
        ConversationRepository,
        "add_message",
        staticmethod(add_message),
    )
    monkeypatch.setattr(
        GeminiAgent,
        "_build_config",
        classmethod(build_config),
    )
    monkeypatch.setattr(
        ToolRegistry,
        "execute",
        staticmethod(execute),
    )
    monkeypatch.setattr(
        llm_provider,
        "generate_content",
        generate_content,
    )

    result = GeminiAgent.run(
        message="Search and analyze Python jobs.",
        profile_id=1,
        db=db,
        conversation_id=conversation_id,
    )

    assert result["message"] == (
        "I completed all five tool rounds and summarized the results."
    )

    assert len(result["tool_calls"]) == 5
    assert len(result["tool_results"]) == 5
    assert all(item.success for item in result["tool_results"])

    assert len(generate_calls) == 6
    assert generate_calls[-1]["enable_tools"] is False

    assert len(config_calls) == 2
    assert config_calls[0]["enable_tools"] is True
    assert config_calls[1]["enable_tools"] is False

    assert stored_messages[-1].role == "assistant"
    assert stored_messages[-1].content == result["message"]
