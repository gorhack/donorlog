from typing import Optional

from pydantic import BaseModel

from app.apis.utils import TotalAndMonthAmount


class User(BaseModel):
    github_username: str
    github_auth_token: str
    opencollective_id: Optional[str] = None


class DisplayUser(BaseModel):
    github_username: str
    github: Optional[TotalAndMonthAmount] = None
    opencollective: Optional[TotalAndMonthAmount] = None
