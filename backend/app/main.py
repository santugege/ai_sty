from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from urllib.parse import urlsplit, urlunsplit

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.account_repository import AccountRepository
from app.account_service import AccountService, AccountServiceError, user_to_dto
from app.agent_openai import request_conversation_summary, request_conversation_turn
from app.agent_repository import AgentRepository
from app.agent_service import (
    AgentInputError,
    AgentServiceError,
    ChatGptConversationService,
)
from app.agent_tools import GptImage2EditTool, create_openai_image_client
from app.auth_dependencies import (
    get_current_user,
    get_optional_current_user,
    require_admin_user,
)
from app.auth_schemas import (
    AdminPasswordResetRequest,
    AdminUserUpdateRequest,
    AuthEnvelope,
    LoginRequest,
    RegisterRequest,
    UserListEnvelope,
)
from app.auth_security import (
    SESSION_COOKIE_NAME,
    make_session_token,
    session_cookie_secure,
    session_expires_at,
)
from app.config import load_backend_env, openai_base_url

load_backend_env()

from app.db import get_db_session
from app.image_storage import MinioImageStorage
from app.image_request import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_TYPES,
    ImageRequestError,
    validate_image_form,
    validate_uploaded_image_content,
)
from app.openai_images import request_image_from_openai
from app.payment_models import PaymentOrderRow
from app.payment_repository import PaymentRepository
from app.payment_schemas import (
    CreateSubscriptionZpayOrderRequest,
    CreateZpayOrderRequest,
    PaymentOrderEnvelope,
)
from app.payment_service import (
    PaymentService,
    PaymentServiceError,
    next_order_no,
    payment_order_to_dto,
)
from app.subscription_models import SubscriptionPlanRow
from app.subscription_repository import SubscriptionRepository
from app.subscription_schemas import (
    EntitlementEnvelope,
    SubscriptionPlanInput,
    SubscriptionPlanListEnvelope,
)
from app.subscription_service import (
    SubscriptionLimitError,
    SubscriptionService,
    SubscriptionServiceError,
    subscription_plan_to_dto,
    yuan_to_cents,
)
from app.user_models import UserRow

logger = logging.getLogger(__name__)
conversation_service: ChatGptConversationService | None = None


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
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, error: HTTPException):
    return JSONResponse(
        {"error": error.detail},
        status_code=error.status_code,
        headers=error.headers,
    )


def build_conversation_service() -> ChatGptConversationService:
    global conversation_service
    if conversation_service is not None:
        return conversation_service

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
        return request_conversation_turn(
            api_key=api_key,
            agent_model=agent_model,
            base_url=base_url,
            **kwargs,
        )

    conversation_service = ChatGptConversationService(
        planner,
        {"gpt_image_2_edit": GptImage2EditTool(image_client=image_client, image_model=image_model)},
    )
    return conversation_service


def build_image_storage() -> MinioImageStorage:
    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT", endpoint)
    return MinioImageStorage(
        bucket=os.getenv("MINIO_BUCKET", "agent-images"),
        endpoint_url=endpoint,
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        public_endpoint=public_endpoint,
    )


def build_agent_service(db: Session | None = None) -> ChatGptConversationService:
    if db is None:
        return build_conversation_service()

    api_key = os.getenv("OPENAI_API_KEY") or ""
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    agent_model = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.4-mini")
    base_url = openai_base_url()
    image_client = create_openai_image_client(
        api_key=api_key,
        image_model=image_model,
        base_url=base_url,
    )

    def planner(**kwargs):
        return request_conversation_turn(
            api_key=api_key,
            agent_model=agent_model,
            base_url=base_url,
            **kwargs,
        )

    def summarizer(**kwargs):
        return request_conversation_summary(
            api_key=api_key,
            agent_model=agent_model,
            base_url=base_url,
            **kwargs,
        )

    return ChatGptConversationService(
        planner=planner,
        tools={
            "gpt_image_2_edit": GptImage2EditTool(
                image_client=image_client,
                image_model=image_model,
            )
        },
        repo=AgentRepository(db),
        storage=build_image_storage(),
        summarizer=summarizer,
    )


def build_account_service(db: Session) -> AccountService:
    return AccountService(AccountRepository(db))


def build_payment_service(db: Session) -> PaymentService:
    return PaymentService(PaymentRepository(db))


def build_subscription_service(db: Session) -> SubscriptionService:
    return SubscriptionService(SubscriptionRepository(db))


def set_session_cookie(response: Response, user: UserRow) -> None:
    expires_at = session_expires_at()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=make_session_token(str(user.id), expires_at),
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        expires=expires_at,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
    )


def auth_error_response(error: AccountServiceError) -> JSONResponse:
    return JSONResponse({"error": str(error)}, status_code=error.status_code)


def agent_error_response(error: Exception) -> JSONResponse:
    if isinstance(error, AgentInputError):
        return JSONResponse({"error": str(error)}, status_code=error.status_code)

    if isinstance(error, ImageRequestError):
        return JSONResponse({"error": error.message}, status_code=error.status_code)

    logger.exception("Agent service failed")
    if isinstance(error, AgentServiceError):
        return JSONResponse({"error": str(error)}, status_code=error.status_code)

    return JSONResponse({"error": "Agent request failed."}, status_code=500)


def payment_error_response(error: PaymentServiceError) -> JSONResponse:
    return JSONResponse({"error": str(error)}, status_code=error.status_code)


def subscription_error_response(error: SubscriptionServiceError) -> JSONResponse:
    if isinstance(error, SubscriptionLimitError):
        return JSONResponse(error.payload, status_code=error.status_code)
    return JSONResponse({"error": str(error)}, status_code=error.status_code)


def plan_from_input(payload: SubscriptionPlanInput) -> SubscriptionPlanRow:
    return SubscriptionPlanRow(
        code=payload.code or payload.name.lower().replace(" ", "-"),
        name=payload.name,
        description=payload.description,
        price_cents=yuan_to_cents(payload.price),
        daily_image_limit=payload.dailyImageLimit,
        monthly_image_limit=payload.monthlyImageLimit,
        is_active=payload.isActive,
        is_default=payload.isDefault,
        sort_order=payload.sortOrder,
    )


def run_agent_service(method_name: str, *args, **kwargs):
    service = build_conversation_service()
    method = getattr(service, method_name)
    return method(*args, **kwargs)


async def read_agent_upload(image: UploadFile) -> tuple[bytes, str, str]:
    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if not image_bytes:
        raise AgentInputError("上传的图片为空。")

    mime_type = image.content_type or ""
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise ImageRequestError(400, "图片格式仅支持 PNG、JPG 或 WebP。")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageRequestError(400, "图片不能超过 10MB。")

    validate_uploaded_image_content(image_bytes, mime_type)
    return image_bytes, image.filename or "product.png", mime_type


async def read_conversation_uploads(
    images: list[UploadFile] | None,
) -> list[dict[str, object]]:
    attachments = []
    for image in images or []:
        image_bytes, image_name, mime_type = await read_agent_upload(image)
        attachments.append(
            {
                "image_bytes": image_bytes,
                "image_name": image_name,
                "mime_type": mime_type,
            }
        )
    return attachments


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/auth/register")
async def register_account(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db_session),
):
    try:
        user = build_account_service(db).register(
            payload.email,
            payload.username,
            payload.password,
        )
        set_session_cookie(response, user)
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/auth/login")
async def login_account(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db_session),
):
    try:
        user = build_account_service(db).login(payload.email, payload.password)
        set_session_cookie(response, user)
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/auth/logout")
async def logout_account(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me")
async def get_auth_user(
    current_user: UserRow | None = Depends(get_optional_current_user),
):
    return AuthEnvelope(
        user=user_to_dto(current_user) if current_user is not None else None
    ).model_dump(mode="json")


@app.get("/api/admin/users")
async def list_admin_users(
    _admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    try:
        users = build_account_service(db).list_users()
        return UserListEnvelope(users=[user_to_dto(user) for user in users]).model_dump(
            mode="json"
        )
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/payments/zpay/orders")
async def create_zpay_payment_order(
    payload: CreateZpayOrderRequest,
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        order = build_payment_service(db).create_zpay_order(
            user=current_user,
            subject=payload.subject,
            amount=payload.amount,
            pay_type=payload.payType,
        )
        return PaymentOrderEnvelope(order=payment_order_to_dto(order)).model_dump(
            mode="json"
        )
    except PaymentServiceError as error:
        return payment_error_response(error)


@app.post("/api/payments/zpay/subscription-orders")
async def create_subscription_zpay_payment_order(
    payload: CreateSubscriptionZpayOrderRequest,
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        subscription_service = build_subscription_service(db)
        plan = subscription_service.repository.get_plan(payload.planId)
        if plan is None or not plan.is_active:
            return JSONResponse({"error": "Subscription plan not found."}, status_code=404)

        if plan.price_cents <= 0:
            payment_repository = PaymentRepository(db)
            active_subscription = subscription_service.repository.get_active_subscription(
                current_user.id,
                datetime.now(timezone.utc),
            )
            if active_subscription is not None and active_subscription.plan_id == plan.id:
                existing_order = (
                    payment_repository.get_paid_subscription_order_by_subscription_id(
                        active_subscription.id
                    )
                )
                if existing_order is not None:
                    return PaymentOrderEnvelope(
                        order=payment_order_to_dto(existing_order)
                    ).model_dump(mode="json")
            else:
                active_subscription = subscription_service.activate_subscription(
                    current_user,
                    plan,
                )
            order = payment_repository.create_order(
                PaymentOrderRow(
                    order_no=next_order_no(),
                    user_id=current_user.id,
                    user_public_id=current_user.user_id,
                    provider="zpay",
                    plan_id=plan.id,
                    order_kind="subscription",
                    subscription_id=active_subscription.id,
                    subject=plan.name,
                    amount_cents=plan.price_cents,
                    pay_type=payload.payType,
                    status="paid",
                    payment_url=None,
                )
            )
        else:
            order = build_payment_service(db).create_subscription_zpay_order(
                user=current_user,
                plan=plan,
                pay_type=payload.payType,
            )
        return PaymentOrderEnvelope(order=payment_order_to_dto(order)).model_dump(
            mode="json"
        )
    except PaymentServiceError as error:
        return payment_error_response(error)


@app.get("/api/subscription/plans")
async def list_subscription_plans(
    _current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        plans = build_subscription_service(db).list_plans(include_inactive=False)
        return SubscriptionPlanListEnvelope(
            plans=[subscription_plan_to_dto(plan) for plan in plans]
        ).model_dump(mode="json")
    except SubscriptionServiceError as error:
        return subscription_error_response(error)


@app.get("/api/subscription/me")
async def get_subscription_entitlement(
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        entitlement = build_subscription_service(db).get_entitlement(current_user)
        return EntitlementEnvelope(entitlement=entitlement.to_dto()).model_dump(
            mode="json"
        )
    except SubscriptionServiceError as error:
        return subscription_error_response(error)


@app.get("/api/admin/subscription/plans")
async def list_admin_subscription_plans(
    _admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    try:
        plans = build_subscription_service(db).list_plans(include_inactive=True)
        return SubscriptionPlanListEnvelope(
            plans=[subscription_plan_to_dto(plan) for plan in plans]
        ).model_dump(mode="json")
    except SubscriptionServiceError as error:
        return subscription_error_response(error)


@app.post("/api/admin/subscription/plans")
async def create_admin_subscription_plan(
    payload: dict[str, Any],
    _admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    try:
        plan_input = SubscriptionPlanInput(**payload)
        repository = SubscriptionRepository(db)
        if plan_input.isDefault:
            repository.clear_default_plans()
        plan = repository.save_plan(plan_from_input(plan_input))
        return {"plan": subscription_plan_to_dto(plan).model_dump(mode="json")}
    except IntegrityError:
        db.rollback()
        return JSONResponse({"error": "套餐代码已存在。"}, status_code=400)
    except ValidationError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except SubscriptionServiceError as error:
        return subscription_error_response(error)


@app.api_route("/api/payments/zpay/notify", methods=["GET", "POST"])
async def handle_zpay_notify(
    request: Request,
    db: Session = Depends(get_db_session),
):
    params: dict[str, object] = dict(request.query_params)
    if request.method == "POST":
        form = await request.form()
        params.update(dict(form))
    try:
        payment_repository = PaymentRepository(db)
        order_no = str(params.get("out_trade_no") or "").strip()
        order = payment_repository.get_by_order_no(order_no)
        subscription_service = None
        notify_user = None
        if order is not None and order.order_kind == "subscription":
            subscription_service = build_subscription_service(db)
            notify_user = AccountRepository(db).get_by_id(order.user_id)

        PaymentService(payment_repository).handle_zpay_notify(
            params,
            subscription_service=subscription_service,
            user=notify_user,
        )
        return Response("success", media_type="text/plain")
    except PaymentServiceError as error:
        logger.warning("ZPAY notify rejected: %s", error)
        return Response("fail", status_code=error.status_code, media_type="text/plain")


@app.patch("/api/admin/users/{user_id}")
async def update_admin_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    try:
        user = build_account_service(db).update_user(
            user_id,
            email=payload.email,
            username=payload.username,
            is_active=payload.isActive,
            acting_user=admin_user,
        )
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/admin/users/{user_id}/password")
async def reset_admin_user_password(
    user_id: str,
    payload: AdminPasswordResetRequest,
    _admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    try:
        user = build_account_service(db).reset_password(user_id, payload.password)
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/agent/conversation")
async def send_conversation_message(
    message: str = Form(""),
    size: str = Form("1536x1024"),
    images: list[UploadFile] | None = File(None),
    _current_user: UserRow = Depends(get_current_user),
):
    try:
        attachments = await read_conversation_uploads(images)
        envelope = await run_in_threadpool(
            run_agent_service,
            "send_message",
            message=message,
            attachments=attachments,
            size=size,
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/conversation/reset")
async def reset_conversation(
    _current_user: UserRow = Depends(get_current_user),
):
    try:
        envelope = await run_in_threadpool(
            run_agent_service,
            "reset",
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.get("/api/agent/sessions")
async def list_agent_sessions(
    _current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        envelope = build_agent_service(db).list_sessions()
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/sessions")
async def create_agent_session(
    message: str = Form(""),
    size: str = Form("1536x1024"),
    images: list[UploadFile] | None = File(None),
    _current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        attachments = await read_conversation_uploads(images)
        envelope = build_agent_service(db).create_session(
            message=message,
            attachments=attachments,
            size=size,
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.get("/api/agent/sessions/{session_id}")
async def get_agent_session(
    session_id: UUID,
    _current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        envelope = build_agent_service(db).get_session(session_id)
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/sessions/{session_id}/messages")
async def send_agent_session_message(
    session_id: UUID,
    message: str = Form(""),
    size: str = Form("1536x1024"),
    images: list[UploadFile] | None = File(None),
    _current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        attachments = await read_conversation_uploads(images)
        envelope = build_agent_service(db).send_session_message(
            session_id,
            message=message,
            attachments=attachments,
            size=size,
        )
        return envelope.model_dump(mode="json")
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
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
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
        subscription_service = build_subscription_service(db)
        entitlement = subscription_service.ensure_can_generate(
            user=current_user,
            requested_images=valid_request.generation_settings.image_count,
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
        subscription_service.record_generation(
            user=current_user,
            entitlement=entitlement,
            image_count=len(generated.images),
        )
        return {
            "image": first_image,
            "images": images_payload,
        }
    except SubscriptionLimitError as error:
        return subscription_error_response(error)
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
