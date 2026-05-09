from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from app.config import openai_client_kwargs


@dataclass(frozen=True)
class AgentTurnDecision:
    action: Literal["edit", "clarify"]
    assistant_message: str
    tool_name: str | None
    tool_instruction: str | None
    response_id: str | None


def request_agent_decision(
    api_key: str,
    agent_model: str,
    user_message: str,
    current_image_summary: str,
    recent_messages: list[dict[str, str]],
    previous_response_id: str | None,
    base_url: str | None = None,
    client_factory: type[Any] = OpenAI,
) -> AgentTurnDecision:
    client = client_factory(**openai_client_kwargs(api_key, base_url))
    response = client.responses.create(
        model=agent_model,
        previous_response_id=previous_response_id,
        input=[
            {
                "role": "system",
                "content": (
                    "You are an ecommerce image editing agent. Decide whether "
                    "the user's request is clear enough to edit the current "
                    "product image or whether you need a clarification. Return "
                    "JSON only with action, assistant_message, tool_name, and "
                    "tool_instruction. Use tool_name gpt_image_2_edit only "
                    "when action is edit."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_message": user_message,
                        "current_image_summary": current_image_summary,
                        "recent_messages": recent_messages,
                    }
                ),
            },
        ],
    )

    try:
        payload = json.loads(response.output_text)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Agent decision response was not valid JSON.") from error

    if not isinstance(payload, dict):
        raise RuntimeError("Agent decision response was not valid JSON.")

    action = payload.get("action")
    if action not in {"edit", "clarify"}:
        raise RuntimeError("Agent decision action was invalid.")

    assistant_message = payload.get("assistant_message")
    tool_name = payload.get("tool_name")
    tool_instruction = payload.get("tool_instruction")
    if not isinstance(assistant_message, str):
        raise RuntimeError("Agent decision response was not valid JSON.")
    if not assistant_message.strip():
        raise RuntimeError("Agent decision response was not valid JSON.")
    if tool_name is not None and not isinstance(tool_name, str):
        raise RuntimeError("Agent decision response was not valid JSON.")
    if tool_instruction is not None and not isinstance(tool_instruction, str):
        raise RuntimeError("Agent decision response was not valid JSON.")
    if action == "edit" and (
        tool_name != "gpt_image_2_edit"
        or tool_instruction is None
        or not tool_instruction.strip()
    ):
        raise RuntimeError("Agent edit decision was invalid.")

    return AgentTurnDecision(
        action=action,
        assistant_message=assistant_message,
        tool_name=tool_name,
        tool_instruction=tool_instruction,
        response_id=getattr(response, "id", None),
    )
