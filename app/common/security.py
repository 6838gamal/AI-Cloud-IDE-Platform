"""Security utilities: password hashing, token generation, session helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any

from app.config import settings


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), token_hash)


def create_signed_payload(payload: dict[str, Any]) -> str:
    """Create a signed payload string for state/CSRF tokens."""
    import base64
    import json

    payload["ts"] = int(time.time())
    raw = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(settings.secret_key.encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + sig).decode()


def verify_signed_payload(token: str, max_age: int = 600) -> dict[str, Any] | None:
    import base64
    import json

    try:
        decoded = base64.urlsafe_b64decode(token.encode())
        raw, sig = decoded.rsplit(b".", 1)
        expected_sig = hmac.new(settings.secret_key.encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(raw)
        if max_age > 0 and int(time.time()) - payload.get("ts", 0) > max_age:
            return None
        return payload
    except Exception:
        return None


def generate_csrf_token() -> str:
    return create_signed_payload({"csrf": secrets.token_hex(16)})


def verify_csrf_token(token: str) -> bool:
    return verify_signed_payload(token, max_age=3600) is not None
