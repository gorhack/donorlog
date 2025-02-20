from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TotalAndMonthAmount:
    month: int
    total: int
    last_checked: datetime


@dataclass
class GithubUser:
    github_id: str
    github_username: str
    github_auth_token: Optional[str]


@dataclass
class OpencollectiveUser:
    opencollective_id: str
    opencollective_username: str


@dataclass
class User:
    user_id: int
    username: str
    github_user: Optional[GithubUser] = None
    opencollective_user: Optional[OpencollectiveUser] = None


@dataclass
class DisplayUser:
    username: str
    github: Optional[TotalAndMonthAmount] = None
    opencollective: Optional[TotalAndMonthAmount] = None

    def total(self):
        return (getattr(getattr(self, 'github', None), 'total', None) or 0) + (getattr(
            getattr(self, 'opencollective', None), 'total', None) or 0)

    def month(self):
        return (getattr(getattr(self, 'github', None), 'month', None) or 0) + (getattr(
            getattr(self, 'opencollective', None), 'month', None) or 0)
