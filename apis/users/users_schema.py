from pydantic import BaseModel


class User(BaseModel):
    email: str
    github_username: str
    github_auth_token: str


class DisplayUser(BaseModel):
    github_username: str
    github_monthly_sponsorship_amount: int
