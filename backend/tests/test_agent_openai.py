import json
from types import SimpleNamespace

import pytest

from app.agent_openai import request_agent_decision, request_conversation_summary


def test_request_conversation_summary_sends_json_content_and_returns_output_text():
    calls = []

    class FakeResponse:
        output_text = "User wants a bright product image with clean background."

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    summary = request_conversation_summary(
        api_key="sk-test",
        agent_model="gpt-5.4-mini",
        previous_summary="User prefers clean backgrounds.",
        recent_messages=[
            {"role": "user", "content": "Make it brighter."},
            {"role": "assistant", "content": "Done."},
        ],
        client_factory=FakeClient,
    )

    assert summary == "User wants a bright product image with clean background."
    assert calls[0]["model"] == "gpt-5.4-mini"
    content = calls[0]["input"][1]["content"]
    assert isinstance(content, str)
    payload = json.loads(content)
    assert payload["previous_summary"] == "User prefers clean backgrounds."
    assert payload["recent_messages"] == [
        {"role": "user", "content": "Make it brighter."},
        {"role": "assistant", "content": "Done."},
    ]


def test_request_conversation_summary_accepts_raw_string_response():
    class FakeResponses:
        def create(self, **kwargs):
            return "  User wants a brighter image with a clean background.  "

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    summary = request_conversation_summary(
        api_key="sk-test",
        agent_model="gpt-5.4-mini",
        previous_summary=None,
        recent_messages=[],
        client_factory=FakeClient,
    )

    assert summary == "User wants a brighter image with a clean background."


def test_request_conversation_summary_raises_for_empty_output():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(output_text="   ")

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent summary response was empty."):
        request_conversation_summary(
            api_key="sk-test",
            agent_model="gpt-5.4-mini",
            previous_summary=None,
            recent_messages=[],
            client_factory=FakeClient,
        )


def test_request_agent_decision_returns_edit_decision_from_gpt_5_5():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_123",
                output_text=(
                    '{"action":"edit","assistant_message":"I will edit it.",'
                    '"tool_name":"gpt_image_2_edit",'
                    '"tool_instruction":"Make it brighter."}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_agent_decision(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it brighter",
        current_image_summary="Current product image exists.",
        recent_messages=[],
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert calls[0]["model"] == "gpt-5.5"
    assert "previous_response_id" not in calls[0]
    assert decision.action == "edit"
    assert decision.tool_name == "gpt_image_2_edit"
    assert decision.response_id == "resp_123"


def test_request_agent_decision_keeps_context_in_messages_not_previous_response_id():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_124",
                output_text=(
                    '{"action":"clarify","assistant_message":"What should change?",'
                    '"tool_name":null,"tool_instruction":null}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    request_agent_decision(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it better",
        current_image_summary="Current product image exists.",
        recent_messages=[],
        previous_response_id="resp_previous",
        client_factory=FakeClient,
    )

    assert "previous_response_id" not in calls[0]
    encoded_input = calls[0]["input"][1]["content"]
    assert "Make it better" in encoded_input


def test_request_agent_decision_accepts_raw_json_string_response():
    class FakeResponses:
        def create(self, **kwargs):
            return (
                '{"action":"edit","assistant_message":"I will edit it.",'
                '"tool_name":"gpt_image_2_edit",'
                '"tool_instruction":"Make it brighter."}'
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_agent_decision(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it brighter",
        current_image_summary="Current product image exists.",
        recent_messages=[],
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.action == "edit"
    assert decision.tool_name == "gpt_image_2_edit"
    assert decision.response_id is None


def test_request_agent_decision_accepts_json_inside_markdown_response():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_markdown",
                output_text=(
                    "```json\n"
                    '{"action":"edit","assistant_message":"I will edit it.",'
                    '"tool_name":"gpt_image_2_edit",'
                    '"tool_instruction":"Make it brighter."}'
                    "\n```"
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_agent_decision(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it brighter",
        current_image_summary="Current product image exists.",
        recent_messages=[],
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.action == "edit"
    assert decision.tool_instruction == "Make it brighter."
    assert decision.response_id == "resp_markdown"


def test_request_agent_decision_passes_base_url_to_client_factory():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_125",
                output_text=(
                    '{"action":"clarify","assistant_message":"What should change?",'
                    '"tool_name":null,"tool_instruction":null}'
                ),
            )

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.responses = FakeResponses()

    request_agent_decision(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it better",
        current_image_summary="Current product image exists.",
        recent_messages=[],
        previous_response_id=None,
        base_url="https://api.example.test/v1",
        client_factory=FakeClient,
    )

    assert calls == [
        {"api_key": "key", "base_url": "https://api.example.test/v1"}
    ]


def test_request_agent_decision_raises_for_invalid_json_output():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(id="resp_125", output_text="not json")

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent decision response was not valid JSON."):
        request_agent_decision(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            current_image_summary="Current product image exists.",
            recent_messages=[],
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_agent_decision_raises_for_edit_with_wrong_tool_name():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_126",
                output_text=(
                    '{"action":"edit","assistant_message":"I will edit it.",'
                    '"tool_name":"other_tool",'
                    '"tool_instruction":"Make it brighter."}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent edit decision was invalid."):
        request_agent_decision(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            current_image_summary="Current product image exists.",
            recent_messages=[],
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_agent_decision_raises_for_edit_with_empty_tool_instruction():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_127",
                output_text=(
                    '{"action":"edit","assistant_message":"I will edit it.",'
                    '"tool_name":"gpt_image_2_edit",'
                    '"tool_instruction":"  "}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent edit decision was invalid."):
        request_agent_decision(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            current_image_summary="Current product image exists.",
            recent_messages=[],
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_agent_decision_raises_for_invalid_action():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_128",
                output_text=(
                    '{"action":"delete","assistant_message":"I will edit it.",'
                    '"tool_name":"gpt_image_2_edit",'
                    '"tool_instruction":"Make it brighter."}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent decision action was invalid."):
        request_agent_decision(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            current_image_summary="Current product image exists.",
            recent_messages=[],
            previous_response_id=None,
            client_factory=FakeClient,
        )
