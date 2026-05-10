from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from app.config import openai_client_kwargs


@dataclass(frozen=True)
class ConversationTurnDecision:
    action: Literal["answer", "edit"]
    assistant_message: str
    tool_name: str | None
    tool_instruction: str | None
    response_id: str | None


AgentTurnDecision = ConversationTurnDecision


def request_conversation_turn(
    api_key: str,
    agent_model: str,
    user_message: str,
    recent_messages: list[dict[str, str]],
    has_current_image: bool,
    uploaded_image_count: int,
    previous_response_id: str | None,
    base_url: str | None = None,
    client_factory: type[Any] = OpenAI,
) -> ConversationTurnDecision:
    client = client_factory(**openai_client_kwargs(api_key, base_url))
    response = client.responses.create(
        model=agent_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a ChatGPT-style ecommerce image assistant. Keep one "
                    "continuous conversation in mind. Users may upload images in "
                    "any turn and ask for edits or normal answers. Return JSON "
                    "only with action, assistant_message, tool_name, and "
                    "tool_instruction. Use action edit and tool_name "
                    "gpt_image_2_edit when the user wants an image changed or "
                    "generated from the current image context. Use action answer "
                    "for clarifying questions, confirmations, or text-only help."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_message": user_message,
                        "recent_messages": recent_messages,
                        "has_current_image": has_current_image,
                        "uploaded_image_count": uploaded_image_count,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return parse_conversation_turn_response(response)


def request_agent_decision(
    api_key: str,
    agent_model: str,
    user_message: str,
    current_image_summary: str = "",
    recent_messages: list[dict[str, str]] | None = None,
    previous_response_id: str | None = None,
    base_url: str | None = None,
    client_factory: type[Any] = OpenAI,
) -> ConversationTurnDecision:
    return request_conversation_turn(
        api_key=api_key,
        agent_model=agent_model,
        user_message=user_message,
        recent_messages=recent_messages or [],
        has_current_image=bool(current_image_summary),
        uploaded_image_count=0,
        previous_response_id=previous_response_id,
        base_url=base_url,
        client_factory=client_factory,
    )


def request_conversation_summary(
    api_key: str,
    agent_model: str,
    previous_summary: str | None,
    recent_messages: list[dict[str, str]],
    base_url: str | None = None,
    client_factory: type[Any] = OpenAI,
) -> str:
    client = client_factory(**openai_client_kwargs(api_key, base_url))
    response = client.responses.create(
        model=agent_model,
        input=[
            {
                "role": "system",
                "content": (
                    "Summarize this image editing conversation for future context. "
                    "Keep stable user preferences, current goal, visual constraints, "
                    "and unresolved questions. Return only the summary text."
                ),
            },
            {
                "role": "user",
                "content": {
                    "previous_summary": previous_summary or "",
                    "recent_messages": recent_messages,
                },
            },
        ],
    )
    return str(response.output_text).strip()


def parse_conversation_turn_response(response: Any) -> ConversationTurnDecision:
    try:
        payload = _loads_response_payload(_response_output_text(response))
    except (AttributeError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Agent decision response was not valid JSON.") from error

    if not isinstance(payload, dict):
        raise RuntimeError("Agent decision response was not valid JSON.")

    action = payload.get("action")
    if action not in {"answer", "edit", "clarify"}:
        raise RuntimeError("Agent decision action was invalid.")

    normalized_action = "answer" if action == "clarify" else action
    assistant_message = payload.get("assistant_message")
    tool_name = payload.get("tool_name")
    tool_instruction = payload.get("tool_instruction")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise RuntimeError("Agent decision response was not valid JSON.")
    if tool_name is not None and not isinstance(tool_name, str):
        raise RuntimeError("Agent decision response was not valid JSON.")
    if tool_instruction is not None and not isinstance(tool_instruction, str):
        raise RuntimeError("Agent decision response was not valid JSON.")
    if normalized_action == "edit" and (
        tool_name != "gpt_image_2_edit"
        or tool_instruction is None
        or not tool_instruction.strip()
    ):
        raise RuntimeError("Agent edit decision was invalid.")

    return ConversationTurnDecision(
        action=normalized_action,
        assistant_message=assistant_message,
        tool_name=tool_name,
        tool_instruction=tool_instruction,
        response_id=getattr(response, "id", None),
    )


def _response_output_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    return response.output_text


def _loads_response_payload(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise
        return json.loads(text[start : end + 1])
