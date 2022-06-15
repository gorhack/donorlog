import os


class Settings:
    PROJECT_NAME: str = "DonorLog"
    PROJECT_VERSION: str = "0.0.1"
    DEBUG: bool = os.getenv("DEBUG", "false") == "true"

    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_PATH = "/oauth/token"
    GITHUB_REDIRECT_URL = os.getenv("APP_DOMAIN") + GITHUB_REDIRECT_PATH
    GITHUB_LOGIN_URL = "https://github.com/login/oauth/authorize?"
    GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_REST_API_URL = "https://api.github.com"
    GITHUB_GRAPHQL_API_URL = f"{GITHUB_REST_API_URL}/graphql"

    GITHUB_TEMP_DB_ACCESS_TOKEN = ""  # TODO: Delete once we have a working database..

    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_ALGORITHM = "HS256"
    TOKEN_EXPIRE_MINUTES = 30


settings = Settings()
