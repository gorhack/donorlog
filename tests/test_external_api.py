import os

import pytest

from app.apis.users.users_schema import GithubUser, OpencollectiveUser
from tests.test_main import async_client, test_total_and_month, add_users_to_database


class TestExternalAPI:
    @pytest.mark.skipif(not os.getenv("GITHUB_GQL_PERSONAL_TOKEN"), reason="Testing Real API")
    async def test_github_graphql(self, async_client):
        await add_users_to_database([(GithubUser(
            github_auth_token=os.getenv("GITHUB_GQL_PERSONAL_TOKEN"),
            github_id="ghid",
            github_username="gorhack",
            amount=test_total_and_month), None)])
        response = await async_client.get("/users/gorhack")
        assert response.json().get("username") == "gorhack"
        assert response.json().get("github").get("month") is not None
        assert response.json().get("github").get("total") is not None
        assert response.json().get("github").get("last_checked") is not None
        assert response.json().get("opencollective") is None
        assert response.status_code == 200

    @pytest.mark.skipif(not os.getenv("OPENCOLLECTIVE_USER_ID"), reason="Testing Real API")
    async def test_opencollective_graphql(self, async_client):
        await add_users_to_database([(OpencollectiveUser(
            opencollective_id=os.getenv("OPENCOLLECTIVE_USER_ID"),
            opencollective_username="gorhack",
            amount=test_total_and_month), None)])
        response = await async_client.get("/users/gorhack")
        assert response.json().get("username") == "gorhack"
        assert response.json().get("github") is None
        assert response.json().get("opencollective") is not None
        assert response.json().get("opencollective").get("month") is not None
        assert response.json().get("opencollective").get("total") is not None
        assert response.json().get("opencollective").get("last_checked") is not None
        assert response.status_code == 200
