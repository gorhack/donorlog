from fastapi import APIRouter, HTTPException, status

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import lookup_by_github_username
from app.apis.users.users_schema import DisplayUser

users_router = APIRouter(prefix="/users", tags=["User API"])


@users_router.get(
    "/{github_username}",
    response_model=DisplayUser,
)
async def search_overview(github_username: str):
    """
    Search for arbitrary user.
    If the user exists in the application, return their sponsorship amounts.
    """
    user = await lookup_by_github_username(github_username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    try:
        github_monthly_sponsorship_amount = await (
            GithubAPI.get_user_sponsorship_amount(user.github_auth_token)
        )
        opencollective_sponsorship_amount = await (
            OpenCollectiveAPI.get_user_sponsorship_amount(user.opencollective_id)
        )
    except HTTPException:  # TODO catch the right errors
        raise HTTPException(  # user's stored auth token is invalid
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    return DisplayUser(
        github_username=github_username,
        github=github_monthly_sponsorship_amount,
        opencollective=opencollective_sponsorship_amount)
