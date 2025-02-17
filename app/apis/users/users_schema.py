from typing import Optional

from pydantic import BaseModel, SkipValidation

from app.apis.utils import TotalAndMonthAmount


class GithubUser(BaseModel):
    github_id: str
    github_username: str
    github_auth_token: Optional[str]

class OpencollectiveUser(BaseModel):
    opencollective_id: str
    opencollective_username: str

class User(BaseModel):
    user_id: int
    username: str
    github_user: Optional[SkipValidation[GithubUser]] = None
    opencollective_user: Optional[SkipValidation[OpencollectiveUser]] = None


class DisplayUser(BaseModel):
    username: str
    github: Optional[TotalAndMonthAmount] = None
    opencollective: Optional[TotalAndMonthAmount] = None

    def total(self):
        return (getattr(getattr(self, 'github', None), 'total', None) or 0) + (getattr(
            getattr(self, 'opencollective', None), 'total', None) or 0)

    def month(self):
        return (getattr(getattr(self, 'github', None), 'month', None) or 0) + (getattr(
            getattr(self, 'opencollective', None), 'month', None) or 0)
