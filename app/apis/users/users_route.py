from fastapi import APIRouter, HTTPException, status

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.apis.users.users_schema import DisplayUser

users_router = APIRouter(prefix="/users", tags=["User API"])


@users_router.get("/{username}",
                  responses={
                      status.HTTP_404_NOT_FOUND: {
                          "description": "User does not exist or not verified."},
                      status.HTTP_200_OK: {"model": DisplayUser}
                  })
async def search_overview(username: str) -> DisplayUser:
    """
    Search for arbitrary user.
    If the user exists in the application, return their sponsorship amounts.
    """
    user = await UsersModel().lookup_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    try:
        github_monthly_sponsorship_amount = await (
            GithubAPI.get_user_sponsorship_amount(user.github_user.github_auth_token)
        ) if user.github_user else None
        opencollective_sponsorship_amount = await (
            OpenCollectiveAPI.get_user_sponsorship_amount(user.opencollective_user.opencollective_id)
        ) if user.opencollective_user else None
    except HTTPException:  # TODO catch the right errors
        raise HTTPException(  # user's stored auth token is invalid
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    return DisplayUser(
        username=username,
        github=github_monthly_sponsorship_amount,
        opencollective=opencollective_sponsorship_amount)
