from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.apis.utils import TotalAndMonthAmount
from app.core.config import settings


class OpenCollectiveOAuth:
    @staticmethod
    def login(state: str):
        params = {
            "client_id": settings.OPENCOLLECTIVE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.OPENCOLLECTIVE_REDIRECT_URL,
            "scope": "",
            "state": state,
        }
        params = urlencode(params)
        return settings.OPENCOLLECTIVE_LOGIN_URL + params

    @staticmethod
    async def get_access_token(code: str):
        try:
            params = {
                "grant_type": "authorization_code",
                "client_id": settings.OPENCOLLECTIVE_CLIENT_ID,
                "client_secret": settings.OPENCOLLECTIVE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.OPENCOLLECTIVE_REDIRECT_URL,
            }
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    settings.OPENCOLLECTIVE_ACCESS_TOKEN_URL, data=params
                )
                if r.status_code == 200:
                    return r.json().get("access_token")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unhandled exception authenticating with OpenCollective: {r.content.decode('utf-8')}",
                    )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Error while trying to retrieve user access token",
            )

    @staticmethod
    async def verify_user_auth_token(opencollective_auth_token):
        auth_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(settings.OPENCOLLECTIVE_GRAPHQL_API_URL,
                                      headers={"authorization": "Bearer " + opencollective_auth_token,
                                               "content-type": "application/json"},
                                      json={"query": "query { me { id } }"})
                status_code = r.status_code
                if status_code == 200:
                    return r.json()["data"]["me"]["id"]
                else:
                    raise auth_error
        except httpx.HTTPError:
            raise auth_error

    @staticmethod
    async def get_user_sponsorship_amount(opencollective_user_id: str) -> Optional[TotalAndMonthAmount]:
        # TODO: Currency differences
        if not opencollective_user_id:
            return None
        start_of_month = datetime.today().strftime("%G-%m-01T00:00:01Z")
        # @formatter:off
        query = (
            "query {"
                f"individual(id: \"{opencollective_user_id}\") {{"
                    "stats {"
                        f"monthContribution: totalAmountSpent(net: true, kind: CONTRIBUTION, dateFrom: \"{start_of_month}\") {{"
                            "valueInCents"
                        "}"
                        f"totalContribution: totalAmountSpent(net: true, kind: CONTRIBUTION, dateFrom: \"1970-01-01T00:00:01Z\") {{"
                            "valueInCents"
                        "}"
                    "}"
                "}"
            "}"
        )
        # @formatter:on
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(settings.OPENCOLLECTIVE_GRAPHQL_API_URL,
                                      headers={"content-type": "application/json"},
                                      json={"query": query})
                status_code = r.status_code
                if status_code == 200:
                    month_contribution = abs(r.json()["data"]["stats"]["monthContribution"]["valueInCents"])
                    total_contribution = abs(r.json()["data"]["stats"]["totalContribution"]["valueInCents"])
                    return TotalAndMonthAmount(
                        month=month_contribution,
                        total=total_contribution,
                        last_checked=datetime.now(tz=timezone.utc)
                    )
                else:
                    return None
        except (httpx.HTTPError, KeyError):
            return None


"""
GraphQL:
individual(id: "{id}" {
    monthly: stats {
        totalAmountSpent(net: true, kind: CONTRIBUTION, dateFrom: "2025-01-01T00:00:01Z") {
            value
            currency
            valueInCents
        }
    }
    total: stats {
        totalAmountSpent(net: true, kind: CONTRIBUTION) {
            value
            currency
            valueInCents
        }
    }
}
"""
