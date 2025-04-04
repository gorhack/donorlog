from typing import Annotated, Optional

from fastapi import Request, Depends, status, APIRouter, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.core.config import templates
from app.session.session_layer import validate_session

profile_router = APIRouter(prefix="/profile", tags=["User Settings and Profile"])


@profile_router.get("", response_class=HTMLResponse)
async def user_profile(request: Request, is_valid_session: bool = Depends(validate_session),
                       alert: Optional[str] = None) -> HTMLResponse:
    if not is_valid_session:
        return HTMLResponse(status_code=status.HTTP_401_UNAUTHORIZED, content="Login to view profile.")
    username = request.session.get("username")

    user = await UsersModel.lookup_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist or not verified.",
        )
    sponsored_nodes = []
    if user.github_user:
        sponsored_nodes.extend(
            await GithubAPI.get_user_sponsorships_as_sponsor(credential=user.github_user.github_auth_token))
    if user.opencollective_user:
        sponsored_nodes.extend(
            await OpenCollectiveAPI.get_user_sponsorships_as_sponsor(
                credential=user.opencollective_user.opencollective_id)
        )
    sponsored_nodes.sort(key=lambda node: node.total, reverse=True)
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "username": username,
            "sponsored_nodes": sponsored_nodes,
            "alert": alert,
            "request": request,
        },
    )


@profile_router.post("", response_class=HTMLResponse, responses={
    status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials."},
    status.HTTP_303_SEE_OTHER: {"description": "Redirect to /profile with success or failure message."}
})
async def change_username(request: Request, username: Annotated[str, Form()],
                          is_valid_session: bool = Depends(validate_session)):
    if not is_valid_session:
        return HTMLResponse(status_code=status.HTTP_401_UNAUTHORIZED, content="Login to view profile.")
    current_username = request.session.get("username")
    user = await UsersModel().lookup_user_by_username(current_username)
    resp = await UsersModel.update_username(user_id=user.user_id, username=username)
    if resp:
        request.session.update({"username": username})
        return RedirectResponse(request.url_for("user_profile").include_query_params(
            alert=f"Updated username from {current_username} to {username}."), status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(request.url_for("user_profile").include_query_params(
            alert=f"Unable to update username to {username}. Choose another."), status_code=status.HTTP_303_SEE_OTHER)
