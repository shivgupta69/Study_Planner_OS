"""Application configuration module."""

from datetime import timedelta
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
INSTANCE_DIR = BACKEND_DIR / "instance"

if load_dotenv:
    load_dotenv(ENV_FILE)


def _resolve_database_path() -> str:
    """Resolve the database path relative to the backend root when needed."""
    raw_path = os.getenv("DATABASE_PATH", "instance/study.db")
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return str(candidate)
    return str((BACKEND_DIR / candidate).resolve())


class Config:
    """Application configuration loaded from environment variables."""

    # Render (and most PaaS providers) expose HTTPS endpoints; detect the
    # platform so we can enforce production safety defaults.
    _IS_RENDER = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))

    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if _IS_RENDER:
            # Fail fast instead of silently booting with a key that is public
            # in the source repository (anyone could forge session cookies).
            raise RuntimeError(
                "SECRET_KEY environment variable is required in production. "
                "Set it in the Render dashboard under Environment "
                "(generate a random value, e.g. `python -c \"import secrets; "
                "print(secrets.token_hex(32))\"`)."
            )
        import warnings
        warnings.warn(
            "SECRET_KEY not found in environment; using an insecure local-dev "
            "fallback. Set SECRET_KEY before deploying anywhere."
        )
        SECRET_KEY = "local-dev-fallback-only"
    DATABASE = _resolve_database_path()
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5081"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Cookies must be HTTPS-only in production (Render serves over HTTPS).
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "1" if _IS_RENDER else "0") == "1"
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
