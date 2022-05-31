from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/search")
async def search_overview_get(github_username: str = ""):
    if not github_username:
        # at least one thing must be searched
        raise HTTPException(
            status_code=400, detail="Must include github_username query parameter."
        )
    return {"github_username": f"{github_username}"}


@app.post("/search")
async def search_overview(github_username: str = Form(default="")):
    if not github_username:
        # at least one thing must be searched
        raise HTTPException(
            status_code=400, detail="Github username must not be empty."
        )
    return await search_overview_get(github_username=github_username)
