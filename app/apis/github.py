from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import status

from app.apis.oauth import OAuth, start_of_month
from app.apis.users.users_schema import TotalAndMonthAmount
from app.core.config import settings


class GithubAPI(OAuth):
    # TODO: follow rate limits
    # https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api

    @staticmethod
    def login(state: str) -> str:
        if not state:
            raise TypeError("state is required")
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URL,
            "state": state,
            "scope": ""  # only access public data... read:user access some private data
        }
        return settings.GITHUB_LOGIN_URL + urlencode(params)

    @staticmethod
    async def get_access_token(code: str) -> str:
        if not code:
            raise TypeError("code cannot be empty")
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
            if r.status_code == status.HTTP_200_OK and not r.json().get("error"):
                return r.json().get("access_token")
            else:
                raise httpx.HTTPError(r.text)

    @staticmethod
    async def get_id_and_username(access_token: str) -> (str, str):
        if not access_token:
            raise TypeError("access_token cannot be empty")
        # @formatter:off
        query = (
            "query {"
                "user: viewer {"
                    "id\n"
                    "username: login"
                "}"
            "}"
        )
        # @formatter:on
        headers = {
            "Authorization": "bearer " + access_token,
            # https://docs.github.com/en/graphql/guides/migrating-graphql-global-node-ids
            "X-Github-Next-Global-ID": "1"
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(settings.GITHUB_GRAPHQL_API_URL, headers=headers, json={"query": query})
            if r.status_code == status.HTTP_200_OK and not r.json().get("errors"):
                return (
                    r.json().get("data").get("user").get("id"),
                    r.json().get("data").get("user").get("username")
                )
            else:
                raise httpx.HTTPError(r.text)

    @staticmethod
    async def get_user_sponsorship_amount(access_token: str) -> Optional[TotalAndMonthAmount]:
        if not access_token:
            return None
        # @formatter:off
        query = (
            "query {"
                "user: viewer {"
                    f"month: totalSponsorshipAmountAsSponsorInCents(since: \"{start_of_month()}\")\n"
                    "total: totalSponsorshipAmountAsSponsorInCents(since: \"1970-01-01T00:00:00Z\")"
                "}"
            "}"
        )
        # @formatter:on
        headers = {"Authorization": "bearer " + access_token}
        async with httpx.AsyncClient() as client:
            r = await client.post(settings.GITHUB_GRAPHQL_API_URL, headers=headers, json={"query": query})
            if r.status_code == status.HTTP_200_OK and not r.json().get("errors"):
                month = r.json().get("data").get("user").get("month")
                total = r.json().get("data").get("user").get("total")
                return TotalAndMonthAmount(
                    month=month,
                    total=total,
                    last_checked=datetime.now(tz=timezone.utc)
                )
            else:
                raise httpx.HTTPError(r.text)
