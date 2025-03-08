from unittest.mock import patch

from app.apis.github import GithubAPI
from tests.test_main import test_total_and_month, async_client, async_client_with_logged_in_user


class TestUserProfile:
    async def test_not_logged_in(self, async_client):
        response = await async_client.get("/profile")
        assert response.status_code == 401


    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    async def test_user_profile(self, _, async_client_with_logged_in_user):
        response = await async_client_with_logged_in_user.get("/profile")
        assert "Welcome test_user_1" in response.text