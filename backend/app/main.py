from __future__ import annotations

import logging
import os
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.image_request import ImageRequestError, validate_image_form
from app.openai_images import request_image_from_openai

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Image Toolbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


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
        )
        generated = await run_in_threadpool(
            request_image_from_openai,
            valid_request,
            api_key=api_key or "",
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        )
        payload = asdict(generated)
        return {
            "image": {
                "src": payload["src"],
                "mimeType": payload["mime_type"],
                "revisedPrompt": payload["revised_prompt"],
            }
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
