from datetime import datetime, timezone

from fastapi import Request

from app.core.config import settings


def is_token_expired(unix_timestamp: int) -> bool:
    if unix_timestamp:
        datetime_from_unix = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        current_time = datetime.now(tz=timezone.utc)
        difference_in_minutes = (datetime_from_unix - current_time).total_seconds() / 60
        return difference_in_minutes <= 0

    return True


def validate_session(request: Request) -> bool:
    session_id = request.session.get("session_id")
    token_exp = request.session.get('token_expiry')

    if not session_id:
        settings.LOG.debug(f"Invalid Session Id: {request.session.get("username")}")
        return False

    if is_token_expired(token_exp):
        settings.LOG.debug(f"Access_token is expired, redirecting to login: {request.session.get("username")}")
        return False

    return True
