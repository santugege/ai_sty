from types import SimpleNamespace

import pytest

from app.agent_openai import request_agent_decision


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
    assert calls[0]["previous_response_id"] is None
    assert decision.action == "edit"
    assert decision.tool_name == "gpt_image_2_edit"
    assert decision.response_id == "resp_123"


def test_request_agent_decision_passes_previous_response_id():
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

    assert calls[0]["previous_response_id"] == "resp_previous"


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
