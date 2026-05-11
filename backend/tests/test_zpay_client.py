from urllib.parse import parse_qs, urlsplit

from app.zpay_client import (
    ZpayConfig,
    build_sign,
    build_submit_payment_url,
    signed_params,
    verify_signature,
)


def test_build_sign_sorts_params_and_ignores_empty_sign_fields():
    params = {
        "pid": "merchant-1",
        "type": "alipay",
        "money": "9.90",
        "name": "Image credits",
        "out_trade_no": "P202605100001",
        "notify_url": "https://example.com/api/payments/zpay/notify",
        "return_url": "https://example.com/payments/return",
        "param": "",
        "sign": "ignored",
        "sign_type": "MD5",
    }

    assert build_sign(params, "secret") == "77c95be797cc50b0febc050772585867"


def test_signed_params_adds_md5_sign_type_and_signature():
    params = {"pid": "merchant-1", "money": "9.90", "name": "Image credits"}

    result = signed_params(params, "secret")

    assert result["sign_type"] == "MD5"
    assert result["sign"] == build_sign(params, "secret")


def test_build_submit_payment_url_contains_signed_zpay_params():
    config = ZpayConfig(
        pid="merchant-1",
        key="secret",
        submit_url="https://zpayz.cn/submit.php",
    )

    payment_url = build_submit_payment_url(
        config=config,
        name="Image credits",
        money="9.90",
        out_trade_no="P202605100001",
        notify_url="https://example.com/api/payments/zpay/notify",
        return_url="https://example.com/payments/return",
        pay_type="alipay",
        param="account=U00000001",
    )

    parsed = urlsplit(payment_url)
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    expected_sign = build_sign(query, "secret")

    assert parsed.scheme == "https"
    assert parsed.netloc == "zpayz.cn"
    assert parsed.path == "/submit.php"
    assert query["pid"] == "merchant-1"
    assert query["type"] == "alipay"
    assert query["money"] == "9.90"
    assert query["out_trade_no"] == "P202605100001"
    assert query["sign_type"] == "MD5"
    assert query["sign"] == expected_sign


def test_verify_signature_rejects_tampered_callback_amount():
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200001",
            "out_trade_no": "P202605100001",
            "type": "alipay",
            "name": "Image credits",
            "money": "9.90",
            "trade_status": "TRADE_SUCCESS",
        },
        "secret",
    )

    assert verify_signature(callback, "secret") is True

    callback["money"] = "0.01"

    assert verify_signature(callback, "secret") is False
