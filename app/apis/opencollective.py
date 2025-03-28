from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import status

from app.apis.oauth import OAuth, start_of_month
from app.apis.users.users_schema import TotalAndMonthAmount, SponsorNode
from app.core.config import settings


class OpenCollectiveAPI(OAuth):
    @staticmethod
    def login(state: str) -> str:
        if not state:
            raise TypeError("state is required")
        params: dict[str, str] = {
            "client_id": settings.OPENCOLLECTIVE_CLIENT_ID,
            "redirect_uri": settings.OPENCOLLECTIVE_REDIRECT_URL,
            "response_type": "code",
            "scope": "",
            "state": state,
        }
        return settings.OPENCOLLECTIVE_LOGIN_URL + urlencode(params)

    @staticmethod
    async def get_access_token(code: str) -> str:
        if not code:
            raise TypeError("code is required")
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
            """
            query {
                "user: me {
                    id
                    username: slug
                }
            }
            """
        )
        # @formatter:on
        headers = {"authorization": "Bearer " + access_token}
        async with httpx.AsyncClient() as client:
            r = await client.post(settings.OPENCOLLECTIVE_GRAPHQL_API_URL, headers=headers, json={"query": query})
            if r.status_code == status.HTTP_200_OK and not r.json().get("errors"):
                return (
                    r.json().get("data").get("user").get("id"),
                    r.json().get("data").get("user").get("username")
                )
            else:
                raise httpx.HTTPError(r.text)

    @staticmethod
    async def get_user_sponsorship_amount(user_id: str) -> Optional[TotalAndMonthAmount]:
        if not user_id:
            return None
        # TODO: Currency differences
        # @formatter:off
        query = (
            f"""
            query {{
                individual(id: \"{user_id}\") {{
                    stats {{
                        month: totalAmountSpent(net: true, kind: CONTRIBUTION, dateFrom: \"{start_of_month()}\") {{
                            valueInCents
                        }}
                        total: totalAmountSpent(net: true, kind: CONTRIBUTION) {{
                            valueInCents
                        }}
                    }}
                }}
            }}
            """
        )
        # @formatter:on
        headers = {"content-type": "application/json"}
        async with httpx.AsyncClient() as client:
            r = await client.post(settings.OPENCOLLECTIVE_GRAPHQL_API_URL, headers=headers, json={"query": query})
            if r.status_code == status.HTTP_200_OK and not r.json().get("errors"):
                month = abs(r.json().get("data").get("individual").get("stats").get("month").get("valueInCents"))
                total = abs(r.json().get("data").get("individual").get("stats").get("total").get("valueInCents"))
                return TotalAndMonthAmount(
                    month=month,
                    total=total,
                    last_checked=datetime.now(tz=timezone.utc)
                )
            else:
                raise httpx.HTTPError(r.text)

    @staticmethod
    async def get_user_sponsorships_as_sponsor(credential: str, cursor: str = "0") -> list[SponsorNode]:
        if not credential:
            return []
        # only return the 100 most backed accounts
        # TODO: utilize offset to return more than 100 possible backed users/organizations
        query = (
            f"""
            query {{
                account(id: \"{credential}\") {{
                    memberOf(role: BACKER, orderBy: {{field: TOTAL_CONTRIBUTED, direction: ASC}}, offset: {cursor}) {{
                        totalCount
                        nodes {{
                            totalDonations {{
                                valueInCents
                            }}
                            account {{
                                slug
                                imageUrl
                            }}
                        }}
                    }}
                }}
            }}"""
        )
        headers = {"content-type": "application/json"}
        slugs = set()
        sponsor_nodes: list[SponsorNode] = []
        async with httpx.AsyncClient() as client:
            r = await client.post(settings.OPENCOLLECTIVE_GRAPHQL_API_URL, headers=headers, json={"query": query})
            if r.status_code == status.HTTP_200_OK and not r.json().get("errors"):
                nodes = r.json().get("data").get("account").get("memberOf").get("nodes")
                for node in nodes:
                    slug = node.get("account").get("slug")
                    # OC returns duplicates if previously start/stopped current backing
                    if slug not in slugs:
                        slugs.add(slug)
                        sponsor_nodes.append(SponsorNode(
                            user=slug,
                            url=f'https://opencollective.com/{node.get("account").get("slug")}',
                            avatar_url=node.get("account").get("imageUrl"),
                            total=node.get("totalDonations").get("valueInCents"),
                        ))
                return sponsor_nodes
            else:
                raise httpx.HTTPError(r.text)
