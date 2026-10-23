"""Shared, strict request validation for the local and ASGI support runtimes."""

from email.message import Message

from ai_support import APPS, MAX_PROMPT_BYTES


MAX_SUPPORT_BODY_BYTES = 8192
SUPPORT_READ_TIMEOUT_SECONDS = 2.0


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError("Non-JSON constant")


def _is_supported_content_type(value):
    parsed = Message()
    parsed["Content-Type"] = value
    params = parsed.get_params()
    if (parsed.get_content_type() != "application/json" or not params or
            params[0][0].lower() != "application/json"):
        return False
    parameters = params[1:]
    return (not parameters or
            len(parameters) == 1 and parameters[0][0].lower() == "charset" and
            isinstance(parameters[0][1], str) and
            parameters[0][1].lower() == "utf-8")


def _normalize_common_support_payload(payload):
    if type(payload) is not dict or set(payload) != {"app", "message"}:
        return None
    app, message = payload["app"], payload["message"]
    if type(app) is not str or app not in APPS or type(message) is not str:
        return None
    try:
        message_bytes = len(message.encode("utf-8"))
    except UnicodeError:
        return None
    if not message.strip() or message_bytes > MAX_PROMPT_BYTES:
        return None
    return {"app": app, "feature": "support", "prompt": message}
