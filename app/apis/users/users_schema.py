from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    email: str
    github_username: str
    github_auth_token: str
    opencollective_id: Optional[str] = None


class DisplayOpenCollectiveUser(BaseModel):
    opencollective_monthly_sponsorship_amount: int


class DisplayUser(BaseModel):
    github_username: str
    github_monthly_sponsorship_amount: int
    opencollective_user: Optional[DisplayOpenCollectiveUser] = None
