from fastapi import APIRouter, HTTPException, status

from app.apis.github import GithubOAuth
from app.apis.users import users_schema
from app.apis.users.users_model import lookup_by_github_username
from app.apis.users.users_schema import DisplayUser

users_router = APIRouter(prefix="/users", tags=["User API"])


async def verify_user_auth_token(user: users_schema.User):
    if (
            user
            and user.github_auth_token
            and await GithubOAuth.verify_user_auth_token(user.github_auth_token)
    ):
        return True
    else:
        return False


@users_router.get(
    "/{github_username}",
    response_model=DisplayUser,
)
async def search_overview(github_username: str):
    """
    Search for arbitrary user.
    If the GitHub user exists in the application, return their monthly sponsorship amount.
    """
    user = await lookup_by_github_username(github_username)
    if not user and not await verify_user_auth_token(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    try:
        github_monthly_sponsorship_amount = await (
            GithubOAuth.get_user_monthly_sponsorship_amount(user.github_auth_token, github_username)
        )
    except HTTPException:
        raise HTTPException(  # user's stored auth token is invalid
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    return {
        "github_username": f"{github_username}",
        "github_monthly_sponsorship_amount": int(github_monthly_sponsorship_amount),
    }
