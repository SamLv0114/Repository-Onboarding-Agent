"""Toy example for integration tests; NEVER use this as real authentication."""


def require_user(token: str) -> str:
    """Validate the token before a protected handler runs."""
    if token != "demo-token":
        raise PermissionError("Invalid demo token")
    return "demo-user"
