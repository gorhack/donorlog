import uuid
from abc import ABC
from datetime import timedelta, datetime
from typing import Optional

from pydantic import BaseModel

from core.config import settings


class UserTokenId(BaseModel):
    key: str
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str


class Payload(BaseModel):
    key: str
    username: str
    issued_at: datetime
    expired_at: datetime


class TokenMaker(ABC):
    # TODO: use PASETO tokens: https://dev.to/techschoolguru/how-to-create-and-verify-jwt-paseto-token-in-golang-1l5j
    def create_token(self, username: str, duration: Optional[timedelta] = None) -> str:
        raise NotImplementedError()


def new_payload(username: str, duration: Optional[timedelta] = None) -> Payload:
    token_key = str(uuid.uuid4())
    if duration:
        expire = datetime.utcnow() + duration
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    payload = Payload(
        key=token_key,
        username=username,
        issued_at=datetime.utcnow(),
        expired_at=expire,
    )
    return payload
