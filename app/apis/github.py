from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.apis.users.users_schema import User
from app.core.config import settings


# Extended from: https://github.com/rohanshiva/Github-Login-FastAPI


class GithubOAuth:
    @staticmethod
    def login(state: str):
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URL,
            "state": state,
            "scope": ""  # only access public data... read:user access some private data
        }
        params = urlencode(params)
        return settings.GITHUB_LOGIN_URL + params

    @staticmethod
    async def get_access_token(code: str):
        try:
            params = {
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URL,
            }
            headers = {"Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    settings.GITHUB_ACCESS_TOKEN_URL, headers=headers, data=params
                )
                if r.status_code == 200 and not r.json().get("error"):
                    return r.json().get("access_token")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unhandled exception authenticating with Github: {r.content.decode('utf-8')}",
                    )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Error while trying to retrieve user access token",
            )

    @staticmethod
    async def get_user_details(access_token) -> User:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": "token " + access_token},
                )
                if r.status_code == 200 and not r.json().get("error"):
                    email = r.json().get("email")
                    username = r.json().get("login")
                    return User(email=email, github_username=username, github_auth_token="")
                else:
                    raise HTTPException(
                        status_code=r.status_code, detail=r.content.decode("utf-8")
                    )
        except httpx.HTTPError:
            raise HTTPException(status_code=401, detail="Failed to fetch user details")

    @staticmethod
    async def get_user_monthly_sponsorship_amount(access_token, username) -> int:
        # TODO totalRecurringMonthlyPriceInCents does not include one-time sponshorships
        # TODO should handle failure more gracefully than returning a 401
        # @formatter:off
        query = (
            "query {"
                f'user(login: "{username}") {{'
                    "sponsorshipsAsSponsor {"
                        "totalRecurringMonthlyPriceInCents"
                    "}"
                "}"
            "}"
        )
        # @formatter:on
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    settings.GITHUB_GRAPHQL_API_URL,
                    headers={"Authorization": "bearer " + access_token},
                    json={"query": query},
                )
                if r.status_code == 200:
                    return r.json()["data"]["user"]["sponsorshipsAsSponsor"][
                        "totalRecurringMonthlyPriceInCents"
                    ]
                else:
                    raise HTTPException(status_code=r.status_code, detail=r.text)
        except httpx.HTTPError:
            raise HTTPException(status_code=401, detail="Failed to fetch user details")

    @staticmethod
    async def get_user_total_sponsorship_amount(access_token, username) -> int:
        # @formatter:off
        query = (
            "query {"
                f'user(login: "{username}") {{'
                    "totalSponsorshipAmountAsSponsorInCents(since: \"1970-01-01T12:00:00\")"
                "}"
            "}"
        )
        # @formatter:on
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    settings.GITHUB_GRAPHQL_API_URL,
                    headers={"Authorization": "bearer " + access_token},
                    json={"query": query},
                )
                if r.status_code == 200:
                    return r.json()["data"]["user"]["totalSponsorshipAmountAsSponsorInCents"]
                else:
                    raise HTTPException(status_code=r.status_code, detail=r.text)
        except httpx.HTTPError:
            raise HTTPException(status_code=401, detail="Failed to fetch user details")

    @staticmethod
    async def verify_user_auth_token(github_auth_token):
        auth_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            token_url = f"{settings.GITHUB_REST_API_URL}/applications/{settings.GITHUB_CLIENT_ID}/token"
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    token_url,
                    auth=(settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET),
                    headers={
                        "accept": "Application/vnd.github.v3+json",
                    },
                    json={"access_token": github_auth_token},
                )
                if r.status_code == 200:
                    return True
                else:
                    raise auth_error
        except httpx.HTTPError:
            raise auth_error

# query = (
#     "query {"
#         "viewer {{"
#             "total: totalSponsorshipAmountAsSponsorInCents(since: \"1970-01-01T12:00:00\")"
#             "month: totalSponsorshipAmountAsSponsorInCents(since: \"2025-01-01T12:00:00\")"
#         "}"
#     "}"
# )