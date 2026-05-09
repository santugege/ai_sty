from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.agent_openai import request_agent_decision
from app.agent_repository import AgentRepository
from app.agent_service import AgentInputError, AgentServiceError, ImageAgentService
from app.agent_tools import GptImage2EditTool, create_openai_image_client
from app.config import load_backend_env, openai_base_url

load_backend_env()

from app.db import SessionLocal
from app.image_storage import LocalImageStorage
from app.image_request import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_TYPES,
    ImageRequestError,
    validate_image_form,
    validate_uploaded_image_content,
)
from app.openai_images import request_image_from_openai

logger = logging.getLogger(__name__)


def frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGIN", "")
    origins = [
        origin.strip()
        for origin in configured.split(",")
        if origin.strip()
    ] or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    for origin in list(origins):
        alias = local_origin_alias(origin)
        if alias and alias not in origins:
            origins.append(alias)
    return origins


def local_origin_alias(origin: str) -> str | None:
    parsed = urlsplit(origin)
    hostname = parsed.hostname
    if hostname not in {"localhost", "127.0.0.1"}:
        return None
    alias_host = "127.0.0.1" if hostname == "localhost" else "localhost"
    alias_netloc = alias_host
    if parsed.port:
        alias_netloc = f"{alias_netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, alias_netloc, "", "", ""))


app = FastAPI(title="Image Toolbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def build_agent_service(db: Session) -> ImageAgentService:
    api_key = os.getenv("OPENAI_API_KEY") or ""
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    agent_model = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.5")
    base_url = openai_base_url()
    image_client = create_openai_image_client(
        api_key=api_key,
        image_model=image_model,
        base_url=base_url,
    )

    def planner(**kwargs):
        return request_agent_decision(
            api_key=api_key,
            agent_model=agent_model,
            base_url=base_url,
            **kwargs,
        )

    return ImageAgentService(
        AgentRepository(db),
        LocalImageStorage(),
        planner,
        {"gpt_image_2_edit": GptImage2EditTool(image_client=image_client, image_model=image_model)},
    )


def agent_error_response(error: Exception) -> JSONResponse:
    if isinstance(error, AgentInputError):
        return JSONResponse({"error": str(error)}, status_code=error.status_code)

    if isinstance(error, ImageRequestError):
        return JSONResponse({"error": error.message}, status_code=error.status_code)

    logger.exception("Agent service failed")
    if isinstance(error, AgentServiceError):
        return JSONResponse({"error": str(error)}, status_code=error.status_code)

    return JSONResponse({"error": "Agent request failed."}, status_code=500)


def run_agent_service(method_name: str, *args, **kwargs):
    with SessionLocal() as db:
        service = build_agent_service(db)
        method = getattr(service, method_name)
        return method(*args, **kwargs)


async def read_agent_upload(image: UploadFile) -> tuple[bytes, str, str]:
    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if not image_bytes:
        raise AgentInputError("Please upload the initial product image.")

    mime_type = image.content_type or ""
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise ImageRequestError(400, "鍥剧墖鏍煎紡浠呮敮鎸?PNG銆丣PG 鎴?WebP銆?")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageRequestError(400, "鍥剧墖涓嶈兘瓒呰繃 10MB銆?")

    validate_uploaded_image_content(image_bytes, mime_type)
    return image_bytes, image.filename or "product.png", mime_type


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/agent/sessions")
async def create_agent_session(
    instruction: str = Form(""),
    size: str = Form("1536x1024"),
    image: UploadFile | None = File(None),
):
    try:
        if image is None:
            raise AgentInputError("Please upload the initial product image.")
        image_bytes, image_name, mime_type = await read_agent_upload(image)
        envelope = await run_in_threadpool(
            run_agent_service,
            "create_session",
            instruction=instruction,
            image_bytes=image_bytes,
            image_name=image_name,
            mime_type=mime_type,
            size=size,
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/sessions/{session_id}/messages")
async def send_agent_message(
    session_id: UUID,
    payload: dict[str, str],
):
    try:
        envelope = await run_in_threadpool(
            run_agent_service,
            "send_message",
            session_id,
            payload.get("instruction", ""),
            payload.get("size", "1536x1024"),
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.get("/api/agent/sessions/{session_id}")
def get_agent_session(session_id: UUID):
    try:
        return run_agent_service("get_session", session_id).model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/sessions/{session_id}/versions/{version_id}/restore")
def restore_agent_version(
    session_id: UUID,
    version_id: UUID,
):
    try:
        return run_agent_service("restore_version", session_id, version_id).model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/images/generate")
async def generate_image(
    toolId: str = Form(...),
    prompt: str = Form(""),
    size: str = Form(""),
    platformStyle: str = Form(""),
    imagePurpose: str = Form(""),
    productCategory: str = Form(""),
    sellingPoints: str = Form(""),
    sceneStyle: str = Form(""),
    visualTone: str = Form(""),
    promotionText: str = Form(""),
    preserveRequirements: str = Form(""),
    avoidElements: str = Form(""),
    aspectRatio: str = Form(""),
    imageCount: str = Form(""),
    image: UploadFile | None = File(None),
):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        valid_request = await validate_image_form(
            toolId,
            prompt,
            size,
            image,
            api_key,
            platform_style=platformStyle,
            image_purpose=imagePurpose,
            product_category=productCategory,
            selling_points=sellingPoints,
            scene_style=sceneStyle,
            visual_tone=visualTone,
            promotion_text=promotionText,
            preserve_requirements=preserveRequirements,
            avoid_elements=avoidElements,
            aspect_ratio=aspectRatio,
            image_count=imageCount,
        )
        image_request_kwargs = {
            "api_key": api_key or "",
            "model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        }
        base_url = openai_base_url()
        if base_url:
            image_request_kwargs["base_url"] = base_url
        generated = await run_in_threadpool(
            request_image_from_openai,
            valid_request,
            **image_request_kwargs,
        )
        images_payload = [
            {
                "src": image.src,
                "mimeType": image.mime_type,
                "revisedPrompt": image.revised_prompt,
            }
            for image in generated.images
        ]
        first_image = images_payload[0]
        return {
            "image": first_image,
            "images": images_payload,
        }
    except ImageRequestError as error:
        return JSONResponse({"error": error.message}, status_code=error.status_code)
    except Exception as error:
        logger.exception("Image generation failed")
        return JSONResponse(
            {"error": public_error_message(error)},
            status_code=502,
        )


def public_error_message(error: Exception) -> str:
    message = str(error)

    if "content policy" in message.lower() or "safety" in message.lower():
        return "请求未通过图片安全审核，请调整描述后重试。"

    if message == "OpenAI 没有返回图片结果。":
        return message

    return "图片生成失败，请稍后重试。"
