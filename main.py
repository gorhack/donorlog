import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from apis.github import GithubOAuth

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))

github_oauth_handler = GithubOAuth()


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    github_username: str = None,
    github_monthly_sponsorship_amount: int = None,
):  # TODO remove query params and retrieve data from db
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "github_username": github_username,
            "github_monthly_sponsorship_amount": github_monthly_sponsorship_amount,
        },
    )


@app.get("/search/{github_username}")
async def search_overview(
    github_username: str, github_monthly_sponsorship_amount: str = ""
):
    # TODO remove query params and retrieve data from db
    if not github_monthly_sponsorship_amount:
        # at least one thing must be searched
        raise HTTPException(
            status_code=400,
            detail="Must include valid github_monthly_sponsorship_amount query parameter.",
        )
    return {
        "github_username": f"{github_username}",
        "github_monthly_sponsorship_amount": int(github_monthly_sponsorship_amount),
    }


@app.post("/search", response_class=RedirectResponse)
async def redirect_search(
    github_username: str = Form(default=""),
    github_monthly_sponsorship_amount: str = Form(default=None),
):
    if not github_username:
        # at least one thing must be searched
        raise HTTPException(
            status_code=400, detail="Github username must not be empty."
        )
    params = {"github_monthly_sponsorship_amount": github_monthly_sponsorship_amount}
    return RedirectResponse(
        f"/search/{github_username}?{urllib.parse.urlencode(params)}",
        status_code=303,
    )


@app.get("/github/login")
def github_login():
    return RedirectResponse(github_oauth_handler.login())


@app.get("/authenticate/github")
def github_authenticate(code: str):
    try:
        access_token = github_oauth_handler.get_access_token(code)
        user = github_oauth_handler.get_user_details(access_token)
        username = user["username"]
        monthly_sponsorship_amount = (
            github_oauth_handler.get_user_monthly_sponsorship_amount(
                access_token, username
            )
        )
        # TODO store access_token and user in db instead of passing as query params
        params = {
            "github_username": username,
            "github_monthly_sponsorship_amount": monthly_sponsorship_amount,
        }
        return RedirectResponse(
            url=app.url_path_for(
                name="root",
            )
            + f"?{urllib.parse.urlencode(params)}"
        )
    except HTTPException:
        raise HTTPException(
            status_code=400, detail="Unhandled exception authenticating with Github"
        )
