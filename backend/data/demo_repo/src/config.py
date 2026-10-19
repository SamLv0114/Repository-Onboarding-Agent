"""Settings for the synthetic demo project."""

DATABASE_URL = "sqlite:///demo.db"


def get_environment() -> str:
    return "development"
