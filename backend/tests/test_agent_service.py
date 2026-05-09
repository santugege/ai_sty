import pytest

from app.agent_service import (
    ChatGptConversationService,
    ConversationInputError,
    ConversationTurnDecision,
)
from app.agent_tools import AgentToolContext, AgentToolResult


class FakeTool:
    name = "gpt_image_2_edit"
    description = "fake"

    def __init__(self):
        self.calls = []

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        self.calls.append(context)
        return AgentToolResult(
            image_bytes=b"edited-image",
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt="edited prompt",
            model="gpt-image-2",
        )


def make_service(decision: ConversationTurnDecision, tool=None):
    planner_calls = []

    def fake_planner(**kwargs):
        planner_calls.append(kwargs)
        return decision

    image_tool = tool or FakeTool()
    service = ChatGptConversationService(
        planner=fake_planner,
        tools={"gpt_image_2_edit": image_tool},
    )
    return service, planner_calls, image_tool


def test_first_turn_stores_messages_and_uploaded_image_in_memory():
    service, planner_calls, tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="已按你的要求调整图片。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Make the background cleaner.",
            response_id="resp_1",
        )
    )

    envelope = service.send_message(
        message="背景更干净一些",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    assert envelope.conversation.id == "default"
    assert envelope.conversation.previousResponseId == "resp_1"
    assert [message.role for message in envelope.messages] == ["user", "assistant"]
    assert envelope.messages[0].attachments[0].src.startswith("data:image/png;base64,")
    assert envelope.currentImage.src.startswith("data:image/png;base64,")
    assert envelope.currentImage.prompt == "Make the background cleaner."
    assert tool.calls[0].image_bytes == b"input-image"
    assert planner_calls[0]["recent_messages"][0]["role"] == "user"


def test_follow_up_without_new_upload_uses_current_image_context():
    service, _planner_calls, tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="已生成第一版。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Create a clean ecommerce scene.",
            response_id="resp_1",
        )
    )
    service.send_message(
        message="先做成电商主图",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    service.planner = lambda **kwargs: ConversationTurnDecision(
        action="edit",
        assistant_message="已继续在当前图上调整。",
        tool_name="gpt_image_2_edit",
        tool_instruction="Make it warmer.",
        response_id="resp_2",
    )
    envelope = service.send_message(
        message="再暖一点",
        attachments=[],
        size="1536x1024",
    )

    assert len(envelope.messages) == 4
    assert envelope.messages[-2].content == "再暖一点"
    assert envelope.messages[-1].content == "已继续在当前图上调整。"
    assert tool.calls[-1].image_bytes == b"edited-image"
    assert envelope.conversation.previousResponseId == "resp_2"


def test_text_only_clarification_does_not_require_image_after_context_exists():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="已生成第一版。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Create a clean ecommerce scene.",
            response_id="resp_1",
        )
    )
    service.send_message(
        message="先做成电商主图",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    service.planner = lambda **kwargs: ConversationTurnDecision(
        action="answer",
        assistant_message="可以，我会沿用当前图片方向。",
        tool_name=None,
        tool_instruction=None,
        response_id="resp_2",
    )
    envelope = service.send_message("明白了吗？", [], "1536x1024")

    assert envelope.messages[-1].role == "assistant"
    assert envelope.messages[-1].content == "可以，我会沿用当前图片方向。"
    assert envelope.currentImage is not None


def test_uploaded_image_remains_context_when_turn_only_answers():
    service, _planner_calls, tool = make_service(
        ConversationTurnDecision(
            action="answer",
            assistant_message="我看到了这张商品图。",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_1",
        )
    )
    first = service.send_message(
        message="先看看这张图",
        attachments=[
            {
                "image_bytes": b"uploaded-context",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    assert first.currentImage is not None
    assert first.currentImage.model == "user-upload"

    service.planner = lambda **kwargs: ConversationTurnDecision(
        action="edit",
        assistant_message="已基于刚才的图片编辑。",
        tool_name="gpt_image_2_edit",
        tool_instruction="Change the background to white.",
        response_id="resp_2",
    )
    service.send_message(
        message="换成白底",
        attachments=[],
        size="1536x1024",
    )

    assert tool.calls[-1].image_bytes == b"uploaded-context"


def test_first_turn_requires_message_or_image():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision("answer", "请上传图片或输入需求。", None, None, "resp")
    )

    with pytest.raises(ConversationInputError, match="请输入消息或上传图片。"):
        service.send_message("", [], "1536x1024")


def test_image_edit_requires_uploaded_or_current_image():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="我需要图片才能编辑。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Edit it.",
            response_id="resp_1",
        )
    )

    with pytest.raises(ConversationInputError, match="请先上传一张图片。"):
        service.send_message("把背景换成白色", [], "1536x1024")


def test_reset_clears_the_single_in_memory_conversation():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision(
            action="answer",
            assistant_message="好的。",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_1",
        )
    )
    service.send_message("你好", [], "1536x1024")

    envelope = service.reset()

    assert envelope.messages == []
    assert envelope.currentImage is None
    assert envelope.conversation.previousResponseId is None
