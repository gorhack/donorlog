from datetime import timedelta
from typing import Optional

from jose import jwt, JWTError

from core.config import settings
from core.token import TokenMaker, new_payload, UserTokenId


class JWTMaker(TokenMaker):
    def create_token(
        self, username: str, duration: Optional[timedelta] = None
    ) -> Optional[str]:
        payload = new_payload(username=username, duration=duration)
        to_encode: dict = {
            "sub": payload.username,
            "exp": payload.expired_at,
            "iat": payload.issued_at,
            "jti": payload.key,
        }
        try:
            jwt_token = jwt.encode(
                claims=to_encode,
                key=settings.JWT_SECRET,
                algorithm=settings.JWT_ALGORITHM,
            )
            return jwt_token
        except JWTError:
            return None


def new_jwt_maker() -> TokenMaker:
    if len(settings.JWT_SECRET if settings.JWT_SECRET else "") < 32:
        raise ValueError("JWT secret key must be at least 32 characters")
    return JWTMaker()


def verify_jwt(token: str) -> Optional[UserTokenId]:
    if not token:
        return None
    payload = jwt.decode(
        token=token,
        key=settings.JWT_SECRET,
        options={"require_exp": True, "require_sub": True, "require_jti": True},
        algorithms=[settings.JWT_ALGORITHM],
    )
    return UserTokenId(key=payload.get("jti"), username=payload.get("sub"))
