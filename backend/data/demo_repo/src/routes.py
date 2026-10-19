"""Toy routes illustrating where the auth helper is called."""

from .auth import require_user


def get_profile(token: str) -> dict[str, str]:
    user_id = require_user(token)
    return {"user_id": user_id, "type": "demo"}
