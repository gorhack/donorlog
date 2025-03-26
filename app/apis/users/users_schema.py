from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TotalAndMonthAmount:
    month: int
    total: int
    last_checked: datetime

@dataclass
class UserRank:
    month_rank: int
    total_rank: int
    total: int
    def __post_init__(self):
        if self.month_rank > self.total:
            self.month_rank = self.total
        if self.total_rank > self.total:
            self.total_rank = self.total


@dataclass
class GithubUser:
    github_id: str
    github_username: str
    github_auth_token: Optional[str]
    amount: TotalAndMonthAmount

@dataclass
class SponsorNode:
    user: str
    url: str
    avatar_url: str
    total: int = 0

@dataclass
class OpencollectiveUser:
    opencollective_id: str
    opencollective_username: str
    amount: TotalAndMonthAmount


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

    def last_checked_str(self):
        return max(getattr(getattr(self, 'github', datetime.min), 'last_checked', datetime.min).date(),
                   getattr(getattr(self, 'opencollective', datetime.min), 'last_checked',
                           datetime.min).date()).strftime("%b %d, %Y")


@dataclass
class User:
    user_id: int
    username: str
    github_user: Optional[GithubUser] = None
    opencollective_user: Optional[OpencollectiveUser] = None

    def display(self) -> DisplayUser:
        return DisplayUser(
            username=self.username,
            github=(getattr(getattr(self, 'github_user', None), 'amount', None)),
            opencollective=(getattr(getattr(self, 'opencollective_user', None), 'amount', None)),
        )

@dataclass
class RankedUsers:
    rank: int
    username: str
    amount: int