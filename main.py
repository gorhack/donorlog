import json
import urllib.parse
import uuid
from base64 import b64encode, b64decode, urlsafe_b64encode
from pathlib import Path
from typing import Optional, Union, Dict

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from fastapi import FastAPI, Request, HTTPException, status, Depends, Response, Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from apis.github import GithubOAuth
from apis.utils import OAuth2AuthorizationWithCookie
from core.config import settings
from core.jwt_token import new_jwt_maker, refresh_jwt
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
github_oauth_handler = GithubOAuth
oauth2_scheme = OAuth2AuthorizationWithCookie(
    authorizationUrl=settings.GITHUB_LOGIN_URL,
    tokenUrl="/oauth/token",
    auto_error=True,
)
# oauth2_scheme_no_error will not display a 401 if unauthenticated resulting in
# automatic user login request. Only used on the root page.
oauth2_scheme_no_error = OAuth2AuthorizationWithCookie(
    authorizationUrl=settings.GITHUB_LOGIN_URL,
    tokenUrl="/oauth/token",
    auto_error=False,
)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))

# key used for state encryption
# not worried about key changing when reloading the application because
# the encrypted state is only used during login process and if it fails
# will just result in the user having to log in again.
STATE_ENCRYPTION_KEY = get_random_bytes(16)


class User(BaseModel):
    user_id: uuid.UUID
    github_username: str
    github_id: int
    github_email: Union[str, None] = None
    github_auth_token: Union[str, None] = None


class DisplayUser(BaseModel):
    github_username: str
    github_monthly_sponsorship_amount: int


class HTTPError(BaseModel):
    detail: str


fake_user_db: Dict[str, User] = {
    "gorhack": User(
        user_id="981a14c0-0fa1-4b89-bc63-cec1e8c70c2d",
        github_username="gorhack",
        github_id=123456,
        github_email="gorhack@example.com",
        github_auth_token=settings.GITHUB_TEMP_DB_ACCESS_TOKEN,
    )
}


def get_user_by_username(db: dict, username: str) -> Optional[User]:
    return db.get(username)


async def verify_user(user: User):
    if (
        user
        and user.github_auth_token
        and await github_oauth_handler.verify_user_auth_token(user.github_auth_token)
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
        user = get_user_by_username(fake_user_db, token.username)
        if await verify_user(user):
            return user
    return None


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    token: UserTokenId = Depends(oauth2_scheme_no_error),
):
    # immediately after logging in, the redirect response from /oauth/token
    # does not contain the token yet in this request
    github_username = ""
    current_user = await get_current_user(token)
    if current_user:
        github_username = current_user.github_username
    return templates.TemplateResponse(
        "index.html",
        {
            "github_username": github_username,
            "request": request,
        },
    )


@app.get(
    "/users/me",
    responses={
        status.HTTP_200_OK: {"model": User},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError},
    },
    tags=["User Information"],
)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.get(
    "/token",
    responses={
        status.HTTP_200_OK: {"model": UserTokenId},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError},
    },
    tags=["User Information"],
)
async def read_user_token(token=Depends(oauth2_scheme)):
    return token


@app.post(
    "/search",
    response_class=RedirectResponse,
    tags=["Search"],
)
async def search_redirect(github_username: str = Form()):
    """
    Search the current authenticated based on the root search form. Redirects to the standard
    GET /search/{github_username}
    """
    return RedirectResponse(
        app.url_path_for("search_overview", github_username=github_username),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get(
    "/search/{github_username}",
    responses={
        status.HTTP_200_OK: {"model": DisplayUser},
        status.HTTP_404_NOT_FOUND: {
            "model": HTTPError,
            "description": "User not verified.",
        },
    },
    tags=["Search"],
)
async def search_overview(github_username: str):
    """
    If the GitHub user has been authenticated, display the monthly sponsorship amount.
    """
    db_user = fake_user_db.get(github_username)
    if not db_user or not await verify_user(db_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not verified.",
        )
    github_monthly_sponsorship_amount = await (
        github_oauth_handler.get_user_monthly_sponsorship_amount(
            db_user.github_auth_token, github_username
        )
    )
    return {
        "github_username": f"{github_username}",
        "github_monthly_sponsorship_amount": int(github_monthly_sponsorship_amount),
    }


def delete_cookies(response: Response, *cookies: str):
    if cookies.count("all") > 0:
        cookies = "gh_login_state", "access_token"
    for cookie in cookies:
        response.delete_cookie(cookie)
    return response


def set_bearer_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite="strict",
    )
    return response


async def cookie_from_access_token(access_token: str):
    user = await github_oauth_handler.get_user_details(access_token)
    username = user.get("username")
    # TODO get_user_by_github_id
    db_user = get_user_by_username(fake_user_db, username)
    if db_user:
        user_id = db_user.user_id
        db_user.github_auth_token = access_token
    else:
        # TODO create db user and let the db create the UUID
        raise NotImplementedError("Unable to create a new user")
    # Note: The JWT stored does not actually contain the access_token from
    # GitHub and requires the database to retrieve the user's stored access_code.
    # Since we have to query the database to retrieve the access_token every time
    # it might be a good idea to just use a session cookie within the db or use
    # JWE to encrypt the payload to include the access token
    return new_jwt_maker().create_token(
        user_id=user_id,
        username=username,
    )


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def handle_401(request: Request, exc: HTTPException):
    if exc.detail == "Token Expired.":
        token = refresh_jwt(fake_user_db, request.cookies.get("access_token"))
        if token:
            resp = RedirectResponse(request.url)
            set_bearer_cookie(resp, token)
            return resp
    if exc.headers and exc.headers.get("WWW-Authenticate") == "Bearer":
        return RedirectResponse(
            app.url_path_for("github_login"), status_code=status.HTTP_303_SEE_OTHER
        )
    resp = RedirectResponse(app.url_path_for("root"))
    delete_cookies(resp, "all")
    # TODO other 401...?
    return resp


@app.get(
    "/login/github",
    response_class=RedirectResponse,
    tags=["Authentication"],
)
async def github_login():
    """
    Redirect the user to log into GitHub.

    ***Cookie: `gh_login_state`*** Sets cookie with
    [AEAD encrypted](https://www.pycryptodome.org/en/v3.14.1/src/cipher/modern.html#eax-mode-1)
    state to prevent CSRF attacks during OAuth.
    """
    # secrets.token_url_safe equivalent
    state = urlsafe_b64encode(get_random_bytes(16)).rstrip(b"=").decode("utf-8")
    resp = RedirectResponse(
        github_oauth_handler.login(state),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    nonce = get_random_bytes(16)
    cipher = AES.new(STATE_ENCRYPTION_KEY, AES.MODE_EAX, nonce)
    ct_state, tag = cipher.encrypt_and_digest(state.encode())
    resp.set_cookie(
        "gh_login_state",
        value=json.dumps(
            {
                "nonce": b64encode(nonce).decode("utf-8"),
                "state": b64encode(ct_state).decode("utf-8"),
                "tag": b64encode(tag).decode("utf-8"),
            }
        ),
        httponly=True,
    )
    return resp


@app.get(
    "/logout",
    tags=["Authentication"],
    response_class=RedirectResponse,
)
async def logout(current_user: Optional[User] = Depends(get_current_user)):
    """
    Remove the JWT from cookies and remove the GitHub access token from the database
    and redirects user to `/`.

    **NOTE:** If the user is not already logged in, will redirect to log in first.
    """
    if current_user:
        current_user.github_auth_token = None
    resp = RedirectResponse(app.url_path_for("root"))
    delete_cookies(resp, "all")
    return resp


@app.get(
    "/oauth/token",
    tags=["Authentication"],
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {"model": Token},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError},
    },
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def access_token_from_authorization_code_flow(
    request: Request, code: str, state: str
):
    """
    This is the reply from the user logging in to GitHub. The request contains the login
    code from the OAuth authorizationCode flow and should contain the same state from
    the `gh_login_state` cookie.
    """
    state_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization check failed due to potential CSRF attack.",
    )
    try:
        cookie_state = json.loads(request.cookies.get("gh_login_state"))
        cipher = AES.new(
            STATE_ENCRYPTION_KEY,
            AES.MODE_EAX,
            nonce=b64decode(cookie_state.get("nonce")),
        )
        pt_state = cipher.decrypt_and_verify(
            b64decode(cookie_state.get("state")), b64decode(cookie_state.get("tag"))
        ).decode("utf-8")
        if state != pt_state:
            raise state_error
    except (ValueError, KeyError):
        raise state_error
    # if the redirect url doesn't match the registered callback URL, GitHub will return 400
    # unhandled exception redirect_uri_mismatch
    redirect_uri = request.headers.get("referer")
    if not redirect_uri:
        redirect_uri = str(request.base_url)
    access_token = await github_oauth_handler.get_access_token(code, redirect_uri)
    resp = RedirectResponse(redirect_uri)
    delete_cookies(resp, "gh_login_state")
    cookie = await cookie_from_access_token(access_token)
    resp = set_bearer_cookie(resp, cookie)
    return resp


@app.post(
    "/oauth/token",
    tags=["Authentication"],
    responses={
        status.HTTP_200_OK: {"model": Token},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError},
    },
)
async def swagger_access_token_from_authorization_code_flow(request: Request):
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
    access_token = await github_oauth_handler.get_access_token(
        code, urllib.parse.unquote(redirect_uri)
    )
    cookie = await cookie_from_access_token(access_token)
    resp = JSONResponse(
        jsonable_encoder({"access_token": cookie, "token_type": "bearer"})
    )
    resp = set_bearer_cookie(resp, cookie)
    return resp
