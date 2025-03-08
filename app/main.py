import asyncio
import base64
import hashlib
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.apis.users.users_route import users_router, search_overview
from app.apis.users.users_schema import GithubUser, OpencollectiveUser
from app.core import migrate
from app.core.config import settings, templates
from app.core.postgres import database
from app.profile import profile_router
from app.session.session_layer import validate_session


async def update_ranked_users_view(interval: int = 60):
    # Ranked users view must get updated periodically or the results will be stale
    # Total and monthly rankings will only be out-of-date as long as the interval, in seconds.
    while True:
        await UsersModel.update_ranked_users_view()
        settings.LOG.debug("Updated ranked users view.")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await migrate.apply_pending_migrations()
    asyncio.create_task(update_ranked_users_view())
    yield
    await database.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)
app.include_router(users_router)
app.include_router(profile_router)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

OAUTH_STATE_PRIVATE_KEY = secrets.token_bytes(1024)


@app.get("/", response_class=HTMLResponse)
async def root(
        request: Request,
        is_valid_session: bool = Depends(validate_session),
):
    display_user = None
    rank = None
    if is_valid_session:
        try:
            display_user = await search_overview(request.session.get("username"))
            rank = await UsersModel.ranking_for_amount(display_user.month(), display_user.total())
        except HTTPException:
            request.session.clear()
    ranked_total = await UsersModel.ranked_totals(max_num=10)
    ranked_month = await UsersModel.ranked_months(max_num=10)
    date = datetime.now(tz=timezone.utc).strftime("%B %Y")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": display_user,
            "rank": rank,
            "date": date,
            "ranked_total": ranked_total,
            "ranked_month": ranked_month,
            "request": request,
        },
    )


@app.get(
    "/login/github",
    response_class=RedirectResponse,
    tags=["Authentication"],
)
async def github_login(request: Request):
    """
    Redirect the user to log into GitHub.

    ***Session: `state`*** Sets session with decently
    [safe](https://stackoverflow.com/questions/26132066/what-is-the-purpose-of-the-state-parameter-in-oauth-authorization-request)
    [state](https://developers.google.com/identity/openid-connect/openid-connect?hl=en#python) to prevent CSRF attacks
    during OAuth.
    """
    random = secrets.token_bytes(1024)
    signature = hashlib.sha256(random + OAUTH_STATE_PRIVATE_KEY).hexdigest()
    state = base64.urlsafe_b64encode(random).decode() + "." + signature
    request.session.update({"state": state})

    response = RedirectResponse(
        GithubAPI.login(signature),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    return response


@app.get(
    "/login/opencollective",
    response_class=RedirectResponse,
    tags=["Authentication"],
)
async def opencollective_login(request: Request):
    """
    Redirect the user to log into OpenCollective.

    ***Session: `state`*** Sets session with decently
    [safe](https://stackoverflow.com/questions/26132066/what-is-the-purpose-of-the-state-parameter-in-oauth-authorization-request)
    [state](https://developers.google.com/identity/openid-connect/openid-connect?hl=en#python) to prevent CSRF attacks
    during OAuth.
    """
    random = secrets.token_bytes(1024)
    signature = hashlib.sha256(random + OAUTH_STATE_PRIVATE_KEY).hexdigest()
    state = base64.urlsafe_b64encode(random).decode() + "." + signature
    request.session.update({"state": state})

    response = RedirectResponse(
        OpenCollectiveAPI.login(signature),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
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
        status.HTTP_401_UNAUTHORIZED: {"description": "Authorization check failed due to potential CSRF attack."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Database failure... try again later."},
    },
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def access_token_from_authorization_code_flow(
        request: Request, code: str, state: str
):
    """
    This is the reply from the user logging in to GitHub. The request contains the login
    code from the OAuth authorizationCode flow and should contain the same state from
    the session.
    """
    state_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        session_state = request.session.pop("state")
        verify_val = hashlib.sha256(
            base64.urlsafe_b64decode(session_state.split(".")[0]) + OAUTH_STATE_PRIVATE_KEY).hexdigest()
        if verify_val != state:
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
    (session_id, user_id) = (request.session.get("session_id"), request.session.get("user_id")) if validate_session(
        request) else (None, None)
    # TODO: handle errors
    (gh_id, gh_username) = await GithubAPI.get_id_and_username(access_token)
    total_and_month = await GithubAPI.get_user_sponsorship_amount(access_token)
    user = await UsersModel().insert_or_update_github_user(
        github_user=GithubUser(github_id=gh_id, github_username=gh_username, github_auth_token=access_token,
                               amount=total_and_month),
        user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not session_id:
        request.session.update({
            "session_id": secrets.token_urlsafe(1024),
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
        status.HTTP_401_UNAUTHORIZED: {"description": "Authorization check failed due to potential CSRF attack."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Database failure... try again later."},
    },
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def access_token_from_authorization_code_flow(
        request: Request, code: str, state: str
):
    """
    This is the reply from the user logging in to OpenCollective. The request contains the login
    code from the OAuth authorizationCode flow and should contain the same state from
    the session.
    """
    state_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        session_state = request.session.pop("state")
        verify_val = hashlib.sha256(
            base64.urlsafe_b64decode(session_state.split(".")[0]) + OAUTH_STATE_PRIVATE_KEY).hexdigest()
        if verify_val != state:
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
    (session_id, user_id) = (request.session.get("session_id"), request.session.get("user_id")) if validate_session(
        request) else (None, None)
    (oc_id, oc_username) = await OpenCollectiveAPI.get_id_and_username(access_token)
    total_and_month = await OpenCollectiveAPI.get_user_sponsorship_amount(access_token)
    # add opencollective_id to database
    user = await UsersModel().insert_or_update_opencollective_user(
        opencollective_user=OpencollectiveUser(opencollective_id=oc_id, opencollective_username=oc_username,
                                               amount=total_and_month),
        user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not session_id:
        request.session.update({
            "session_id": secrets.token_urlsafe(1024),
            "token_expiry": (
                (datetime.now(tz=timezone.utc) + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp()),
        })
    request.session.update({
        "user_id": user.user_id,
        "username": user.username,
    })
    return response
