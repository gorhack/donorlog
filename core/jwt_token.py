import uuid
from datetime import timedelta
from typing import Optional

from jose import jwt, JWTError

from core.config import settings
from core.token import TokenMaker, new_payload, UserTokenId


class JWTMaker(TokenMaker):
    def create_token(
        self,
        user_id: uuid.UUID,
        username: str,
        duration: Optional[timedelta] = None,
    ) -> Optional[str]:
        payload = new_payload(
            user_id=user_id,
            username=username,
            duration=duration,
        )
        to_encode: dict = {
            "sub": payload.user_id,
            "exp": payload.expired_at,
            "iat": payload.issued_at,
            "jti": payload.token_id,
            "preferred_username": payload.username,
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
    return UserTokenId(
        user_id=payload.get("sub"),
        username=payload.get("preferred_username"),
    )


def refresh_jwt(db: dict, token: str) -> Optional[str]:
    # split removes the "Bearer " from the token
    claims = jwt.get_unverified_claims(token.split(" ")[1])
    user = db.get(claims.get("preferred_username"))
    if user.github_auth_token:
        return new_jwt_maker().create_token(
            user_id=user.user_id,
            username=user.github_username,
        )
    else:
        return None
