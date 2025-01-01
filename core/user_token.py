import uuid
from abc import ABC
from datetime import timedelta, datetime
from typing import Optional

from pydantic import BaseModel

from core.config import settings


class UserTokenId(BaseModel):
    user_id: str
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str


class Payload(BaseModel):
    token_id: str
    user_id: str
    username: str
    issued_at: datetime
    expired_at: datetime


class TokenMaker(ABC):
    # TODO: use PASETO tokens: https://dev.to/techschoolguru/how-to-create-and-verify-jwt-paseto-token-in-golang-1l5j
    def create_token(
        self,
        user_id: uuid.UUID,
        username: str,
        duration: Optional[timedelta] = None,
    ) -> str:
        raise NotImplementedError()


def new_payload(
    user_id: uuid.UUID,
    username: str,
    duration: Optional[timedelta] = None,
) -> Payload:
    if duration:
        expire = datetime.utcnow() + duration
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    payload = Payload(
        token_id=str(uuid.uuid4()),
        user_id=str(user_id),
        username=username,
        issued_at=datetime.utcnow(),
        expired_at=expire,
    )
    return payload
