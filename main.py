import urllib.parse
import uuid
from pathlib import Path
from typing import Optional, Union, Dict

from fastapi import FastAPI, Request, HTTPException, status, Depends, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.responses import JSONResponse

from apis.github import GithubOAuth
from apis.utils import OAuth2AuthorizationWithCookie
from core.config import settings
from core.jwt_token import new_jwt_maker
from core.token import UserTokenId, Token

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.GITHUB_CLIENT_ID,
    },
)
github_oauth_handler = GithubOAuth()
oauth2_scheme = OAuth2AuthorizationWithCookie(
    authorizationUrl=settings.GITHUB_LOGIN_URL,
    tokenUrl="/oauth/token",
    auto_error=False,
)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


class User(BaseModel):
    github_username: str
    github_id: int
    github_email: Union[str, None] = None
    github_auth_token: Union[str, None] = None


fake_user_db: Dict[str, User] = {
    "gorhack": User(
        github_username="gorhack",
        github_id=123456,
        github_email="gorhack@example.com",
        github_auth_token=settings.GITHUB_TEMP_DB_ACCESS_TOKEN,
    )
}


def get_user(db: dict, username: str) -> Optional[User]:
    # TODO use key instead of username
    return db.get(username)


def verify_user(user: User):
    if (
        user
        and user.github_auth_token
        and github_oauth_handler.verify_user_auth_token(user.github_auth_token)
    ):
        return True
    else:
        return False


async def get_current_user(
    token: UserTokenId = Depends(oauth2_scheme),
) -> Optional[User]:
    if not token:
        return None
    if token:
        user = get_user(fake_user_db, token.username)
        if verify_user(user):
            return user
    return None


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request, current_user: Optional[User] = Depends(get_current_user)
):
    github_username = None
    github_monthly_sponsorship_amount = None
    if current_user:
        github_username = current_user.github_username
        github_monthly_sponsorship_amount = (
            github_oauth_handler.get_user_monthly_sponsorship_amount(
                current_user.github_auth_token, github_username
            )
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "github_username": github_username,
            "github_monthly_sponsorship_amount": github_monthly_sponsorship_amount,
        },
    )


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/token")
async def read_items(token=Depends(oauth2_scheme)):
    return {"token": token}


@app.get("/search/{github_username}")
async def search_overview(github_username: str):
    # TODO remove query params and retrieve data from db
    github_monthly_sponsorship_amount = ""
    if not github_monthly_sponsorship_amount:
        # at least one thing must be searched
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return {
        "github_username": f"{github_username}",
        "github_monthly_sponsorship_amount": int(github_monthly_sponsorship_amount),
    }


def set_bearer_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
    )
    return response


def cookie_from_access_token(access_token: str):
    user = github_oauth_handler.get_user_details(access_token)
    username = user.get("username")
    fake_user_db.get(username).github_auth_token = access_token
    # Note: The JWT stored does not actually contain the access_token from
    # GitHub and requires authentication with the database to retrieve the
    # user's stored access_code.
    return new_jwt_maker().create_token(username=username)


@app.post(
    "/login/github",
    response_class=RedirectResponse,
    status_code=303,
    tags=["login"],
)
async def github_login():
    """
    Redirect the user to log into GitHub.

    ***Cookie: `gh_login_state`*** Sets this cookie to prevent CSRF attacks during OAuth.
    """
    state = uuid.uuid4().hex
    resp = RedirectResponse(
        github_oauth_handler.login(state),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    resp.set_cookie("gh_login_state", value=state, httponly=True)
    return resp


@app.get(
    "/oauth/token",
    response_class=RedirectResponse,
    tags=["login"],
    response_model=Token,
)
async def access_token_from_authorization_code_flow(
    request: Request, code: str, state: str
):
    """
    This is the reply from the user logging in to GitHub. The request contains the login
    code from the OAuth authorizationCode flow and should contain the same state from
    the `gh_login_state` cookie.
    """
    if state is not request.cookies.get("gh_login_state"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization check failed due to potential CSRF attack.",
        )
    redirect_uri = request.headers.get("referer")
    if not redirect_uri:
        redirect_uri = str(request.base_url)
    access_token = github_oauth_handler.get_access_token(code, redirect_uri)
    resp = RedirectResponse(redirect_uri)
    resp.delete_cookie("gh_login_state")
    resp.delete_cookie("gh_login_referer")
    cookie = cookie_from_access_token(access_token)
    resp = set_bearer_cookie(resp, cookie)
    return resp


@app.post(
    "/oauth/token",
    response_class=JSONResponse,
    tags=["login"],
    response_model=Token,
)
async def access_token_from_authorization_code_flow(request: Request):
    """
    Swagger OAuth authorizationCode flow. Swagger handles CSRF verification.

    See [here](https://dev.mendeley.com/reference/topics/authorization_auth_code.html)
    for more information on the authorizationCode flow.
    """
    body = await request.body()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request missing body with OAuth code.",
        )
    params = body.decode(encoding="utf-8").split("&")
    code = ""
    redirect_uri = ""
    for p in params:
        if p.startswith("code="):
            code = p.split("=")[1]
        if p.startswith("redirect_uri="):
            redirect_uri = p.split("=")[1]
    access_token = github_oauth_handler.get_access_token(
        code, urllib.parse.unquote(redirect_uri)
    )
    cookie = cookie_from_access_token(access_token)
    resp = JSONResponse(
        jsonable_encoder({"access_token": cookie, "token_type": "bearer"})
    )
    resp = set_bearer_cookie(resp, cookie)
    return resp
