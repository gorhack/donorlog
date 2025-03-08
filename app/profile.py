from fastapi import Request, Depends, status, APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import templates
from app.session.session_layer import validate_session

profile_router = APIRouter(prefix="/profile", tags=["User Settings and Profile"])


@profile_router.get("", response_class=HTMLResponse)
async def user_profile(request: Request, is_valid_session: bool = Depends(validate_session)) -> HTMLResponse:
    if not is_valid_session:
        return HTMLResponse(status_code=status.HTTP_401_UNAUTHORIZED, content="Login to view profile.")
    username = request.session.get("username")
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "username": username,
            "request": request,
        },
    )
