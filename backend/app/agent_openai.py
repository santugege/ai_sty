from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from app.config import openai_client_kwargs
from app.image_prompts import (
    ChatGptImageBrief,
    compose_chatgpt_planner_system_prompt,
    compose_chatgpt_tool_instruction,
)


@dataclass(frozen=True)
class ConversationTurnDecision:
    action: Literal["answer", "generate", "edit"]
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
    summary: str | None = None,
    base_url: str | None = None,
    client_factory: type[Any] = OpenAI,
) -> ConversationTurnDecision:
    client = client_factory(**openai_client_kwargs(api_key, base_url))
    response = client.responses.create(
        model=agent_model,
        input=[
            {
                "role": "system",
                "content": compose_chatgpt_planner_system_prompt(),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_message": user_message,
                        "summary": summary or "",
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
                "content": json.dumps(
                    {
                        "previous_summary": previous_summary or "",
                        "recent_messages": recent_messages,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    summary = _response_output_text(response).strip()
    if not summary:
        raise RuntimeError("Agent summary response was empty.")
    return summary


def parse_conversation_turn_response(response: Any) -> ConversationTurnDecision:
    try:
        payload = _loads_response_payload(_response_output_text(response))
    except (AttributeError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Agent decision response was not valid JSON.") from error

    if not isinstance(payload, dict):
        raise RuntimeError("Agent decision response was not valid JSON.")

    action = payload.get("action")
    if action not in {"answer", "generate", "edit", "clarify"}:
        raise RuntimeError("Agent decision action was invalid.")

    normalized_action = "answer" if action == "clarify" else action
    assistant_message = payload.get("assistant_message")
    tool_name = payload.get("tool_name")
    tool_instruction = payload.get("tool_instruction")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise RuntimeError("Agent decision response was not valid JSON.")
    if tool_name is not None and not isinstance(tool_name, str):
        raise RuntimeError("Agent decision response was not valid JSON.")
    if normalized_action == "generate" and tool_name != "chatgpt_image_generate":
        raise RuntimeError("Agent generate decision was invalid.")
    if normalized_action == "edit" and tool_name != "chatgpt_image_edit":
        raise RuntimeError("Agent edit decision was invalid.")
    if normalized_action in {"generate", "edit"}:
        try:
            rendered_instruction = _render_tool_instruction(tool_instruction)
        except RuntimeError as error:
            if normalized_action == "generate":
                raise RuntimeError("Agent generate decision was invalid.") from error
            raise RuntimeError("Agent edit decision was invalid.") from error
    else:
        if tool_instruction is not None and not isinstance(tool_instruction, str):
            raise RuntimeError("Agent decision response was not valid JSON.")
        rendered_instruction = tool_instruction

    return ConversationTurnDecision(
        action=normalized_action,
        assistant_message=assistant_message,
        tool_name=tool_name,
        tool_instruction=rendered_instruction,
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


def _render_tool_instruction(value: Any) -> str:
    if isinstance(value, str):
        if not value.strip():
            raise RuntimeError("Agent image decision was invalid.")
        return value
    if not isinstance(value, dict):
        raise RuntimeError("Agent image decision was invalid.")
    brief = ChatGptImageBrief(
        user_goal=str(value.get("user_goal") or ""),
        scene=str(value.get("scene") or ""),
        subject=str(value.get("subject") or ""),
        style=str(value.get("style") or ""),
        composition=str(value.get("composition") or ""),
        lighting=str(value.get("lighting") or ""),
        preserve=_string_list(value.get("preserve")),
        change=_string_list(value.get("change")),
        avoid=_string_list(value.get("avoid")),
    )
    rendered = compose_chatgpt_tool_instruction(brief)
    if not rendered.strip():
        raise RuntimeError("Agent image decision was invalid.")
    return rendered


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
