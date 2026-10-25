"""Opt-in server-side Workers AI transport. Construction never performs I/O."""

import http.client
from contextlib import suppress
import json
import math
import re
import ssl
import socket
import threading
import time

from ai_support import (
    MAX_OUTPUT_BYTES, MAX_OUTPUT_TOKENS, MAX_PROMPT_BYTES, MODEL, ProviderResult, SYSTEM_PROMPT,
)
from database import read_secret
from support_http import _reject_json_constant, _unique_json_object


MAX_PROVIDER_RESPONSE_BYTES = 16384


class WorkersAIHTTPTransport:
    def __init__(self, *, account_id, token_file):
        if type(account_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", account_id):
            raise ValueError("An operator-provided Cloudflare account ID is required")
        token = read_secret(token_file)
        if not re.fullmatch(r"[!-~]{1,4096}", token):
            raise ValueError("An operator-provided server-side API token file is required")
        self._account_id = account_id
        self._token = token

    def run(self, *, model, messages, max_tokens, temperature, timeout_seconds):
        if (model != MODEL or max_tokens != MAX_OUTPUT_TOKENS or temperature != 0.2 or
                type(timeout_seconds) not in (int, float) or
                not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 5 or
                type(messages) is not tuple or len(messages) != 2 or
                messages[0] != {"role": "system", "content": SYSTEM_PROMPT} or
                type(messages[1]) is not dict or
                set(messages[1]) != {"role", "content"} or
                messages[1]["role"] != "user" or
                type(messages[1]["content"]) is not str or
                not messages[1]["content"].strip() or
                len(messages[1]["content"].encode("utf-8")) > MAX_PROMPT_BYTES):
            raise ValueError("Unsupported provider request")
        body = json.dumps({
            "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
        }).encode("utf-8")
        connection = http.client.HTTPSConnection(
            "api.cloudflare.com", timeout=timeout_seconds, context=ssl.create_default_context(),
        )
        deadline = time.monotonic() + timeout_seconds
        timer = None
        try:
            # Fixed TLS destination, no environment proxy, redirects or automatic retries.
            connection.connect()
            sock = connection.sock
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Provider connection deadline expired")

            def expire():
                with suppress(OSError):
                    sock.shutdown(socket.SHUT_RDWR)

            # Interrupt even slow-drip response headers, not just idle sockets.
            timer = threading.Timer(remaining, expire)
            timer.daemon = True
            timer.start()
            connection.request(
                "POST", f"/client/v4/accounts/{self._account_id}/ai/run/{MODEL}",
                body=body,
                headers={
                    "Authorization": "Bearer " + self._token,
                    "Content-Type": "application/json", "Accept": "application/json",
                },
            )
            response = connection.getresponse()
            if (response.status != 200 or
                    response.headers.get_content_type() != "application/json" or
                    response.getheader("Content-Encoding") not in (None, "identity")):
                raise ValueError("Provider unavailable")
            length = response.getheader("Content-Length")
            if length is not None and (
                not length.isascii() or not length.isdigit() or
                len(length) > 8 or int(length) > MAX_PROVIDER_RESPONSE_BYTES
            ):
                raise ValueError("Invalid provider response size")
            raw = bytearray()
            while not response.isclosed():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Provider response deadline expired")
                # Keep the live socket reference even when Connection: close is returned.
                sock.settimeout(remaining)
                chunk = response.read1(MAX_PROVIDER_RESPONSE_BYTES + 1 - len(raw))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_PROVIDER_RESPONSE_BYTES:
                    raise ValueError("Provider response too large")
            if time.monotonic() > deadline:
                raise TimeoutError("Provider response deadline expired")
            if length is not None and len(raw) != int(length):
                raise ValueError("Incomplete provider response")
            payload = json.loads(
                raw.decode("utf-8"), object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
            if (type(payload) is not dict or payload.get("success") is not True or
                    payload.get("errors") not in (None, []) or
                    type(payload.get("result")) is not dict):
                raise ValueError("Invalid provider result")
            result = payload["result"]
            text, usage = result.get("response"), result.get("usage")
            if (type(text) is not str or not text.strip() or
                    len(text.encode("utf-8")) > MAX_OUTPUT_BYTES or
                    type(usage) is not dict or
                    type(usage.get("prompt_tokens")) is not int or
                    not 0 <= usage["prompt_tokens"] <= len(body) or
                    type(usage.get("completion_tokens")) is not int or
                    not 0 <= usage["completion_tokens"] <= MAX_OUTPUT_TOKENS):
                raise ValueError("Invalid provider output")
            return ProviderResult(text, usage["prompt_tokens"], usage["completion_tokens"])
        except Exception:
            # Never propagate a token, provider response, prompt or network exception.
            raise RuntimeError("Provider request failed") from None
        finally:
            if timer is not None:
                timer.cancel()
            connection.close()
