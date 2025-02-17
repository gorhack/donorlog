import json
from base64 import b64encode, b64decode, urlsafe_b64encode
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.apis.users.users_route import users_router, search_overview
from app.apis.users.users_schema import GithubUser, OpencollectiveUser
from app.apis.utils import HTTPError
from app.core import migrate
from app.core.config import settings
from app.core.postgres import database
from app.session.session_layer import validate_session, create_random_session_string


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await migrate.apply_pending_migrations()
    yield
    await database.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)
app.include_router(users_router)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))

# key used for state encryption
# not worried about key changing when reloading the application because
# the encrypted state is only used during login process and if it fails
# will just result in the user having to log in again.
STATE_ENCRYPTION_KEY = get_random_bytes(16)


@app.get("/", response_class=HTMLResponse)
async def root(
        request: Request,
        is_valid_session: bool = Depends(validate_session),
):
    display_user = None
    if is_valid_session:
        try:
            display_user = await search_overview(request.session.get("username"))
        except HTTPException:
            request.session.clear()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": display_user,
            "request": request,
        },
    )


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
    response = RedirectResponse(
        GithubAPI.login(state),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    nonce = get_random_bytes(16)
    cipher = AES.new(STATE_ENCRYPTION_KEY, AES.MODE_EAX, nonce)
    ct_state, tag = cipher.encrypt_and_digest(state.encode())
    response.set_cookie(
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
    return response


@app.get(
    "/login/opencollective",
    response_class=RedirectResponse,
    tags=["Authentication"],
)
async def opencollective_login():
    """
    Redirect the user to log into OpenCollective.

    ***Cookie: `oc_login_state`*** Sets cookie with
    [AEAD encrypted](https://www.pycryptodome.org/en/v3.14.1/src/cipher/modern.html#eax-mode-1)
    state to prevent CSRF attacks during OAuth.
    """
    # secrets.token_url_safe equivalent
    state = urlsafe_b64encode(get_random_bytes(16)).rstrip(b"=").decode("utf-8")
    response = RedirectResponse(
        OpenCollectiveAPI.login(state),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    nonce = get_random_bytes(16)
    cipher = AES.new(STATE_ENCRYPTION_KEY, AES.MODE_EAX, nonce)
    ct_state, tag = cipher.encrypt_and_digest(state.encode())
    response.set_cookie(
        "oc_login_state",
        value=json.dumps(
            {
                "nonce": b64encode(nonce).decode("utf-8"),
                "state": b64encode(ct_state).decode("utf-8"),
                "tag": b64encode(tag).decode("utf-8"),
            }
        ),
        httponly=True,
    )
    return response


@app.get(
    "/logout",
    tags=["Authentication"],
    responses={
        status.HTTP_303_SEE_OTHER: {"description": "Redirect to root"},
    }
)
async def logout(request: Request):
    request.session.clear()
    resp = RedirectResponse(url=app.url_path_for("root"), status_code=status.HTTP_303_SEE_OTHER)
    return resp


@app.get(
    "/oauth/gh_token",
    tags=["Authentication"],
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {"description": "Redirect to referer"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError},
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
    access_token = await GithubAPI.get_access_token(code)
    response = RedirectResponse(url=redirect_uri, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("gh_login_state")
    (session_id, user_id) = (request.session.get("session_id"), request.session.get("user_id")) if validate_session(
        request) else (None, None)
    # TODO: handle errors
    (gh_id, gh_username) = await GithubAPI.get_id_and_username(access_token)
    user = await UsersModel().insert_or_update_github_user(
        github_user=GithubUser(github_id=gh_id, github_username=gh_username, github_auth_token=access_token),
        user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failure... try again later.",
        )
    if not session_id:
        request.session.update({
            "session_id": create_random_session_string(),
            "token_expiry": (
                (datetime.now(tz=timezone.utc) + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp()),
        })
    request.session.update({
        "user_id": user.user_id,
        "username": user.username,
    })
    return response


@app.get(
    "/oauth/oc_token",
    tags=["Authentication"],
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {"description": "Redirect to referer"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError},
    },
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def access_token_from_authorization_code_flow(
        request: Request, code: str, state: str
):
    """
    This is the reply from the user logging in to OpenCollective. The request contains the login
    code from the OAuth authorizationCode flow and should contain the same state from
    the `oc_login_state` cookie.
    """
    state_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization check failed due to potential CSRF attack.",
    )
    try:
        cookie_state = json.loads(request.cookies.get("oc_login_state"))
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
    # if the redirect url doesn't match the registered callback URL, OpenCollective will return 400
    # unhandled exception redirect_uri_mismatch
    redirect_uri = request.headers.get("referer")
    if not redirect_uri:
        redirect_uri = str(request.base_url)
    access_token = await OpenCollectiveAPI.get_access_token(code)
    response = RedirectResponse(url=redirect_uri, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("oc_login_state")
    (session_id, user_id) = (request.session.get("session_id"), request.session.get("user_id")) if validate_session(
        request) else (None, None)
    (oc_id, oc_username) = await OpenCollectiveAPI.get_id_and_username(access_token)
    # add opencollective_id to database
    user = await UsersModel().insert_or_update_opencollective_user(
        opencollective_user=OpencollectiveUser(opencollective_id=oc_id, opencollective_username=oc_username),
        user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failure... try again later.",
        )
    if not session_id:
        request.session.update({
            "session_id": create_random_session_string(),
            "token_expiry": (
                (datetime.now(tz=timezone.utc) + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp()),
        })
    request.session.update({
        "user_id": user.user_id,
        "username": user.username,
    })
    return response
