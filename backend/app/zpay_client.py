from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode


@dataclass(frozen=True)
class ZpayConfig:
    pid: str
    key: str
    submit_url: str = "https://zpayz.cn/submit.php"


def build_sign(params: dict[str, object], key: str) -> str:
    payload = _signing_payload(params)
    source = "&".join(f"{name}={value}" for name, value in payload.items())
    return hashlib.md5(f"{source}{key}".encode("utf-8")).hexdigest()


def signed_params(params: dict[str, object], key: str) -> dict[str, str]:
    normalized = _string_params(params)
    normalized["sign"] = build_sign(normalized, key)
    normalized["sign_type"] = "MD5"
    return normalized


def verify_signature(params: dict[str, object], key: str) -> bool:
    provided_sign = str(params.get("sign") or "").lower()
    if not provided_sign:
        return False
    return hmac.compare_digest(provided_sign, build_sign(params, key))


def build_submit_payment_url(
    *,
    config: ZpayConfig,
    name: str,
    money: Decimal | str,
    out_trade_no: str,
    notify_url: str,
    return_url: str,
    pay_type: str,
    param: str = "",
) -> str:
    query = signed_params(
        {
            "pid": config.pid,
            "type": pay_type,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "return_url": return_url,
            "name": name,
            "money": _format_money(money),
            "param": param,
        },
        config.key,
    )
    return f"{config.submit_url}?{urlencode(query)}"


def _format_money(value: Decimal | str) -> str:
    return f"{Decimal(str(value)).quantize(Decimal('0.01'))}"


def _signing_payload(params: dict[str, object]) -> dict[str, str]:
    return {
        name: value
        for name, value in sorted(_string_params(params).items())
        if name not in {"sign", "sign_type"} and value != ""
    }


def _string_params(params: dict[str, object]) -> dict[str, str]:
    return {
        str(name): str(value)
        for name, value in params.items()
        if value is not None
    }
