import json
from types import SimpleNamespace

import pytest

from app.agent_openai import (
    request_conversation_turn_stream,
    request_conversation_summary,
    request_conversation_turn,
)


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


def test_request_conversation_turn_includes_summary_in_model_context():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_123",
                output_text=(
                    '{"action":"answer","assistant_message":"I can help.",'
                    '"tool_name":null,"tool_instruction":null}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Continue the edit",
        recent_messages=[{"role": "user", "content": "Make it brighter."}],
        has_current_image=True,
        uploaded_image_count=0,
        previous_response_id="resp_previous",
        summary="User prefers clean white backgrounds.",
        client_factory=FakeClient,
    )

    payload = json.loads(calls[0]["input"][1]["content"])
    assert payload["summary"] == "User prefers clean white backgrounds."


def test_request_conversation_turn_sends_uploaded_images_to_responses_api():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_vision",
                output_text=(
                    '{"action":"edit","assistant_message":"I can see the scene.",'
                    '"tool_name":"chatgpt_image_edit",'
                    '"tool_instruction":"Apply a Korean style to the visible scene."}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Modify this photo into a Korean style.",
        recent_messages=[],
        has_current_image=True,
        uploaded_image_count=1,
        previous_response_id=None,
        image_inputs=[
            {
                "image_bytes": b"image-bytes",
                "mime_type": "image/png",
            }
        ],
        client_factory=FakeClient,
    )

    content = calls[0]["input"][1]["content"]
    assert content[0]["type"] == "input_text"
    payload = json.loads(content[0]["text"])
    assert payload["user_message"] == "Modify this photo into a Korean style."
    assert content[1] == {
        "type": "input_image",
        "image_url": "data:image/png;base64,aW1hZ2UtYnl0ZXM=",
        "detail": "high",
    }


def test_request_conversation_turn_requests_structured_json_output():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_structured",
                output_text=(
                    '{"action":"generate","assistant_message":"I will create it.",'
                    '"tool_name":"chatgpt_image_generate",'
                    '"tool_instruction":{'
                    '"user_goal":"Create a calm mountain lake.",'
                    '"scene":"Mountain lake at sunrise",'
                    '"subject":"A still lake",'
                    '"style":"Photorealistic",'
                    '"composition":"Wide landscape",'
                    '"lighting":"Soft sunrise",'
                    '"preserve":[],"change":[],"avoid":["watermark"]'
                    "}}"
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Generate a sunrise lake.",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    text_config = calls[0]["text"]
    assert text_config["format"]["type"] == "json_schema"
    assert text_config["format"]["name"] == "chatgpt_conversation_turn"
    assert text_config["format"]["strict"] is True
    assert text_config["format"]["schema"]["required"] == [
        "action",
        "assistant_message",
        "tool_name",
        "tool_instruction",
    ]


def test_request_conversation_turn_accepts_raw_json_string_response():
    class FakeResponses:
        def create(self, **kwargs):
            return (
                '{"action":"edit","assistant_message":"I will edit it.",'
                '"tool_name":"chatgpt_image_edit",'
                '"tool_instruction":"Make it brighter."}'
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it brighter",
        recent_messages=[],
        has_current_image=True,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.action == "edit"
    assert decision.tool_name == "chatgpt_image_edit"
    assert decision.response_id is None


def test_request_conversation_turn_accepts_json_inside_markdown_response():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_markdown",
                output_text=(
                    "```json\n"
                    '{"action":"edit","assistant_message":"I will edit it.",'
                    '"tool_name":"chatgpt_image_edit",'
                    '"tool_instruction":"Make it brighter."}'
                    "\n```"
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it brighter",
        recent_messages=[],
        has_current_image=True,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.action == "edit"
    assert decision.tool_instruction == "Make it brighter."
    assert decision.response_id == "resp_markdown"


def test_request_conversation_turn_passes_base_url_to_client_factory():
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

    request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it better",
        recent_messages=[],
        has_current_image=True,
        uploaded_image_count=0,
        previous_response_id=None,
        base_url="https://api.example.test/v1",
        client_factory=FakeClient,
    )

    assert calls == [
        {"api_key": "key", "base_url": "https://api.example.test/v1"}
    ]


def test_request_conversation_turn_raises_for_invalid_json_output():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(id="resp_125", output_text="not json")

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent decision response was not valid JSON."):
        request_conversation_turn(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            recent_messages=[],
            has_current_image=True,
            uploaded_image_count=0,
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_conversation_turn_raises_for_edit_with_wrong_tool_name():
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
        request_conversation_turn(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            recent_messages=[],
            has_current_image=True,
            uploaded_image_count=0,
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_conversation_turn_raises_for_edit_with_empty_tool_instruction():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_127",
                output_text=(
                    '{"action":"edit","assistant_message":"I will edit it.",'
                    '"tool_name":"chatgpt_image_edit",'
                    '"tool_instruction":"  "}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent edit decision was invalid."):
        request_conversation_turn(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            recent_messages=[],
            has_current_image=True,
            uploaded_image_count=0,
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_conversation_turn_raises_for_invalid_action():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_128",
                output_text=(
                    '{"action":"delete","assistant_message":"I will edit it.",'
                    '"tool_name":"chatgpt_image_edit",'
                    '"tool_instruction":"Make it brighter."}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    with pytest.raises(RuntimeError, match="Agent decision action was invalid."):
        request_conversation_turn(
            api_key="key",
            agent_model="gpt-5.5",
            user_message="Make it brighter",
            recent_messages=[],
            has_current_image=True,
            uploaded_image_count=0,
            previous_response_id=None,
            client_factory=FakeClient,
        )


def test_request_conversation_turn_accepts_generate_action():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_generate",
                output_text=(
                    '{"action":"generate","assistant_message":"I will create it.",'
                    '"tool_name":"chatgpt_image_generate",'
                    '"tool_instruction":{'
                    '"user_goal":"Create a calm mountain lake.",'
                    '"scene":"Mountain lake at sunrise",'
                    '"subject":"A still lake",'
                    '"style":"Photorealistic",'
                    '"composition":"Wide landscape",'
                    '"lighting":"Soft sunrise",'
                    '"preserve":[],'
                    '"change":[],'
                    '"avoid":["watermark"]'
                    "}}"
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Generate a sunrise lake.",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.action == "generate"
    assert decision.tool_name == "chatgpt_image_generate"
    assert "Mountain lake at sunrise" in decision.tool_instruction


def test_request_conversation_turn_uses_chatgpt_general_prompt_without_product_terms():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_answer",
                output_text=(
                    '{"action":"answer","assistant_message":"Please upload an image.",'
                    '"tool_name":null,"tool_instruction":null}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Help me edit an image.",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    system_prompt = calls[0]["input"][0]["content"]
    assert "general ChatGPT-style image assistant" in system_prompt
    assert "Pinduoduo" not in system_prompt
    assert "Taobao" not in system_prompt
    assert "selling point" not in system_prompt


def test_request_conversation_turn_stream_emits_text_deltas_and_final_decision():
    deltas = []

    class FakeEvent:
        def __init__(self, event_type, delta=None):
            self.type = event_type
            self.delta = delta

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def __iter__(self):
            return iter(
                [
                    FakeEvent("response.output_text.delta", '{"action":"answer",'),
                    FakeEvent(
                        "response.output_text.delta",
                        '"assistant_message":"Streaming hello.",',
                    ),
                    FakeEvent(
                        "response.output_text.delta",
                        '"tool_name":null,"tool_instruction":null}',
                    ),
                ]
            )

        def get_final_response(self):
            return SimpleNamespace(
                id="resp_stream",
                output_text=(
                    '{"action":"answer","assistant_message":"Streaming hello.",'
                    '"tool_name":null,"tool_instruction":null}'
                ),
            )

    class FakeResponses:
        def stream(self, **kwargs):
            return FakeStream()

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_conversation_turn_stream(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Hello",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
        on_text_delta=deltas.append,
    )

    assert "".join(deltas) == "Streaming hello."
    assert decision.assistant_message == "Streaming hello."
    assert decision.response_id == "resp_stream"


def test_request_conversation_turn_stream_parses_accumulated_text_when_final_output_is_empty():
    class FakeEvent:
        def __init__(self, event_type, delta=None):
            self.type = event_type
            self.delta = delta

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def __iter__(self):
            return iter(
                [
                    FakeEvent("response.output_text.delta", '{"action":"answer",'),
                    FakeEvent(
                        "response.output_text.delta",
                        '"assistant_message":"Recovered from stream.",',
                    ),
                    FakeEvent(
                        "response.output_text.delta",
                        '"tool_name":null,"tool_instruction":null}',
                    ),
                ]
            )

        def get_final_response(self):
            return SimpleNamespace(id="resp_empty_final", output_text="")

    class FakeResponses:
        def stream(self, **kwargs):
            return FakeStream()

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_conversation_turn_stream(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Hello",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.assistant_message == "Recovered from stream."
    assert decision.response_id == "resp_empty_final"
