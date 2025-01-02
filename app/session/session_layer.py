import logging
import secrets
from datetime import datetime, timezone

from fastapi import Request


# https://medium.com/@maazbinmustaqeem/how-to-easily-validate-user-sessions-in-fastapi-with-dependency-injection-d28baebe6e19
def create_random_session_string() -> str:
    return secrets.token_urlsafe(32)  # Generates a random URL-safe string


def is_token_expired(unix_timestamp: int) -> bool:
    if unix_timestamp:
        datetime_from_unix = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        current_time = datetime.now(timezone.utc)
        difference_in_minutes = (datetime_from_unix - current_time).total_seconds() / 60
        return difference_in_minutes <= 0

    return True


def validate_session(request: Request) -> bool:
    session_id = request.session.get("session_id")
    token_exp = request.session.get('token_expiry')

    if not session_id:
        logging.info("Invalid Session Id")
        return False

    if is_token_expired(token_exp):
        logging.info("Access_token is expired, redirecting to login")
        return False

    return True
