from fastapi import Request, Depends, status, APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.core.config import templates
from app.session.session_layer import validate_session

profile_router = APIRouter(prefix="/profile", tags=["User Settings and Profile"])


@profile_router.get("", response_class=HTMLResponse)
async def user_profile(request: Request, is_valid_session: bool = Depends(validate_session)) -> HTMLResponse:
    if not is_valid_session:
        return HTMLResponse(status_code=status.HTTP_401_UNAUTHORIZED, content="Login to view profile.")
    username = request.session.get("username")
    user = await UsersModel().lookup_user_by_username(username)
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
            await OpenCollectiveAPI.get_user_sponsorships_as_sponsor(credential=user.opencollective_user.opencollective_id)
        )
    sponsored_nodes.sort(key=lambda node: node.total, reverse=True)
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "username": username,
            "sponsored_nodes": sponsored_nodes,
            "request": request,
        },
    )
