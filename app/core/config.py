import logging
import os
from pathlib import Path

from fastapi.templating import Jinja2Templates


class Settings:
    PROJECT_NAME: str = "DonorLog"
    PROJECT_VERSION: str = "0.0.1"
    DEBUG: bool = os.getenv("DEBUG", "false") == "true"

    DATABASE_URL = os.getenv("RDS_DATABASE_URL")

    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_PATH = "/oauth/gh_token"
    GITHUB_REDIRECT_URL = os.getenv("APP_DOMAIN") + GITHUB_REDIRECT_PATH
    GITHUB_LOGIN_URL = "https://github.com/login/oauth/authorize?"
    GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_REST_API_URL = "https://api.github.com"
    GITHUB_GRAPHQL_API_URL = f"{GITHUB_REST_API_URL}/graphql"

    OPENCOLLECTIVE_CLIENT_ID = os.getenv("OPENCOLLECTIVE_CLIENT_ID")
    OPENCOLLECTIVE_CLIENT_SECRET = os.getenv("OPENCOLLECTIVE_CLIENT_SECRET")
    OPENCOLLECTIVE_REDIRECT_PATH = "/oauth/oc_token"
    OPENCOLLECTIVE_REDIRECT_URL = os.getenv("APP_DOMAIN") + OPENCOLLECTIVE_REDIRECT_PATH
    OPENCOLLECTIVE_LOGIN_URL = "https://opencollective.com/oauth/authorize?"
    OPENCOLLECTIVE_ACCESS_TOKEN_URL = "https://opencollective.com/oauth/token"
    OPENCOLLECTIVE_GRAPHQL_API_URL = "https://opencollective.com/api/graphql/v2"

    SESSION_SECRET = os.getenv("SESSION_SECRET")

    LOG = logging.getLogger('uvicorn')
    LOG.setLevel(level=logging.DEBUG if DEBUG else logging.INFO)


settings = Settings()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))
