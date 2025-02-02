import os
from unittest.mock import patch

import pytest

from app.apis.users.users_model import UsersModel
from app.apis.users.users_schema import User
from tests.test_main import async_client


class TestExternalAPI:
    @pytest.mark.skipif(not os.getenv("GITHUB_GQL_PERSONAL_TOKEN"), reason="Testing Real API")
    @patch.object(UsersModel, "lookup_by_github_username",
                  return_value=User(github_username="gorhack",
                                    github_auth_token=os.getenv("GITHUB_GQL_PERSONAL_TOKEN")))
    async def test_github_graphql(self, _, async_client):
        response = await async_client.get("/users/gorhack")
        assert response.json().get("github_username") == "gorhack"
        assert response.json().get("github").get("month") is not None
        assert response.json().get("github").get("total") is not None
        assert response.json().get("github").get("last_checked") is not None
        assert response.json().get("opencollective") is None
        assert response.status_code == 200

    @pytest.mark.skipif(not os.getenv("OPENCOLLECTIVE_USER_ID"), reason="Testing Real API")
    @patch.object(UsersModel, "lookup_by_github_username",
                  return_value=User(github_username="gorhack",
                                    github_auth_token="",
                                    opencollective_id=os.getenv("OPENCOLLECTIVE_USER_ID")))
    async def test_github_graphql(self, _, async_client):
        response = await async_client.get("/users/gorhack")
        assert response.json().get("github_username") == "gorhack"
        assert response.json().get("github") is None
        assert response.json().get("opencollective") is not None
        assert response.json().get("opencollective").get("month") is not None
        assert response.json().get("opencollective").get("total") is not None
        assert response.json().get("opencollective").get("last_checked") is not None
        assert response.status_code == 200
