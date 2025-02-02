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

    def total(self):
        return (getattr(getattr(self, 'github', None), 'total', None) or 0) + (getattr(
            getattr(self, 'opencollective', None), 'total', None) or 0)

    def month(self):
        return (getattr(getattr(self, 'github', None), 'month', None) or 0) + (getattr(
            getattr(self, 'opencollective', None), 'month', None) or 0)
