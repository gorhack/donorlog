# reference: https://github.com/rohanshiva/Github-Login-FastAPI
import os
from urllib.parse import urlencode

import requests
from fastapi import HTTPException
from requests import RequestException

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
LOGIN_URL = os.getenv("GITHUB_LOGIN_URL")
ACCESS_TOKEN_URL = os.getenv("GITHUB_ACCESS_TOKEN_URL")
API_URL = os.getenv("GITHUB_API_URL")


class GithubOAuth:
    @staticmethod
    def login():
        # TODO `state` field to protect against cross-site scripting
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": "read:user",
        }
        params = urlencode(params)
        return LOGIN_URL + params

    @staticmethod
    def get_access_token(code):
        try:
            params = {
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "client_secret": CLIENT_SECRET,
                "code": code,
            }
            headers = {"Accept": "application/json"}
            r = requests.post(ACCESS_TOKEN_URL, headers=headers, params=params)
            access_token = r.json()["access_token"]
            return access_token
        except RequestException:
            raise HTTPException(
                status_code=401,
                detail="Error while trying to retrieve user access token",
            )

    @staticmethod
    def get_user_details(access_token):
        try:
            r = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": "token " + access_token},
            )
            key = str(r.json()["id"])
            email = r.json()["email"]
            username = r.json()["login"]
            avatar_url = r.json()["avatar_url"]
            return {
                "key": key,
                "email": email,
                "username": username,
                "avatar_url": avatar_url,
            }
        except RequestException:
            raise HTTPException(status_code=401, detail="Failed to fetch user details")

    @staticmethod
    def get_user_monthly_sponsorship_amount(access_token, username):
        # TODO: calculate total amount donated, not just current month
        # fmt: off
        query = (
            "query {"
                f'user(login: "{username}") {{'
                    "sponsorshipsAsSponsor(last: 100) {"
                        "totalRecurringMonthlyPriceInDollars"
                    "}"
                "}"
            "}"
        )
        # fmt: on
        try:
            r = requests.post(
                API_URL,
                headers={"Authorization": "bearer " + access_token},
                json={"query": query},
            )
            if r.status_code == 200:
                return r.json()["data"]["user"]["sponsorshipsAsSponsor"][
                    "totalRecurringMonthlyPriceInDollars"
                ]
            else:
                raise HTTPException(status_code=r.status_code, detail=r.content)
        except RequestException:
            raise HTTPException(status_code=401, detail="Failed to fetch user details")
