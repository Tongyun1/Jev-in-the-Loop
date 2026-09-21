"""Conservative label-based guardrails, not a universal side-effect classifier."""

from urllib.parse import urlparse

RISKY_CLICK_TERMS = (
    "submit order",
    "place order",
    "confirm order",
    "confirm booking",
    "complete booking",
    "pay now",
    "proceed to pay",
    "make payment",
    "purchase",
    "buy now",
    "checkout",
    "send message",
    "send email",
    "publish",
    "post comment",
    "delete",
    "remove account",
    "cancel order",
    "cancel booking",
    "cancel reservation",
    "create account",
    "sign up",
    "sign in",
    "log in",
    "save password",
    "save card",
    "提交订单",
    "确认订单",
    "确认预订",
    "完成预订",
    "最后一步",
    "去支付",
    "立即付款",
    "确认支付",
    "购买",
    "结算",
    "发送消息",
    "发送邮件",
    "发布",
    "发表评论",
    "删除",
    "注销账户",
    "取消订单",
    "取消预订",
    "创建账户",
    "注册",
    "登录",
    "保存密码",
    "保存银行卡",
)

SENSITIVE_FILL_TERMS = (
    "password",
    "passcode",
    "otp",
    "verification code",
    "security code",
    "card number",
    "cvv",
    "cvc",
    "passport",
    "identity number",
    "social security",
    "phone",
    "telephone",
    "email",
    "address",
    "guest name",
    "full name",
    "contact name",
    "密码",
    "验证码",
    "动态码",
    "银行卡",
    "卡号",
    "安全码",
    "护照",
    "证件号",
    "身份证",
    "电话号码",
    "手机号",
    "电子邮件",
    "邮箱",
    "地址",
    "住客姓名",
    "联系人",
    "姓名",
)


def _contains(value: str, terms) -> str | None:
    normalized = " ".join(value.casefold().split())
    return next((term for term in terms if term.casefold() in normalized), None)


def action_block_reason(action: dict, stop_before: list[str]) -> str | None:
    label = str(action.get("label", ""))
    custom = _contains(label, stop_before)
    if custom:
        return f"matched caller stop condition: {custom}"
    if action.get("kind") == "fill":
        term = _contains(label, SENSITIVE_FILL_TERMS)
        if term:
            return f"sensitive form field: {term}"
    if action.get("kind") in {"click", "select", "press"}:
        term = _contains(label, RISKY_CLICK_TERMS)
        if term:
            return f"external side-effect boundary: {term}"
    return None


def allowed_url(url: str, allowed_domains: set[str]) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in allowed_domains)


def link_block_reason(action: dict, allowed_domains: set[str]) -> str | None:
    href = action.get("href")
    if not href or not str(href).startswith(("http://", "https://")):
        return None
    if not allowed_url(str(href), allowed_domains):
        return "target link leaves the allowed domains"
    return None
