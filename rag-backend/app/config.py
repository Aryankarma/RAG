import os
from pathlib import Path

from dotenv import load_dotenv

# Load `.env` from the backend project root (`rag-backend/`), not from the shell cwd.
# Otherwise running `uvicorn` from the repo root leaves SMTP and other vars unset.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

# Pinecone namespaces (keep docs separate from chunks)
PINECONE_NAMESPACE_CHUNKS = os.getenv("PINECONE_NAMESPACE_CHUNKS") or "chunks"
PINECONE_NAMESPACE_DOCS = os.getenv("PINECONE_NAMESPACE_DOCS") or "docs"

def _env_str(key: str) -> str | None:
    v = os.getenv(key)
    if v is None:
        return None
    s = v.strip()
    return s if s else None


# SMTP (optional; required only when using send_email tool with confirm)
SMTP_HOST = _env_str("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = _env_str("SMTP_USER")
SMTP_PASSWORD = _env_str("SMTP_PASSWORD")
EMAIL_FROM = _env_str("EMAIL_FROM")
EMAIL_FROM_NAME = _env_str("EMAIL_FROM_NAME") or ""

# send_email: require explicit confirm unless server sets EMAIL_SEND_ENABLED=true
EMAIL_SEND_ENABLED = os.getenv("EMAIL_SEND_ENABLED", "").lower() in ("1", "true", "yes")

# Comma-separated domain suffixes (e.g. "company.com,other.org"); empty = no restriction
_email_allow = os.getenv("EMAIL_ALLOWLIST_DOMAINS") or ""
EMAIL_ALLOWLIST_DOMAINS = tuple(
    d.strip().lower().lstrip("@") for d in _email_allow.split(",") if d.strip()
)
