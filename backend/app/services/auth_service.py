import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from app.db import database

ITERATIONS = 240_000
SESSION_HOURS = 12


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt_text, digest_text = stored.split("$", 3)
        if scheme != "pbkdf2_sha256": return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id: int):
    token = secrets.token_urlsafe(40)
    digest = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    database.save_session(digest, user_id, expires.isoformat(timespec="seconds"))
    return token, expires


def resolve_access_token(token: str):
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return database.get_session_user(digest, now)


def revoke_access_token(token: str):
    database.delete_session(hashlib.sha256(token.encode()).hexdigest())
