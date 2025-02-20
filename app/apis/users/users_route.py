from datetime import datetime, timezone

import httpx
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
        if user.github_user and (
                datetime.now(tz=timezone.utc) - user.github_user.amount.last_checked).days > 0:
            github_monthly_sponsorship_amount = await GithubAPI.get_user_sponsorship_amount(
                user.github_user.github_auth_token)
            user.github_user.amount = github_monthly_sponsorship_amount
            await UsersModel.update_github_total_month(user.github_user, user.user_id)
        if user.opencollective_user and (
                datetime.now(tz=timezone.utc) - user.opencollective_user.amount.last_checked).days > 0:
            opencollective_sponsorship_amount = await (
                OpenCollectiveAPI.get_user_sponsorship_amount(user.opencollective_user.opencollective_id)
            ) if user.opencollective_user else None
            user.opencollective_user.amount = opencollective_sponsorship_amount
            await UsersModel.update_opencollective_total_month(user.opencollective_user, user.user_id)
    except httpx.HTTPError:  # TODO catch the right errors
        raise HTTPException(  # user's stored auth token is invalid
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    return user.display()
