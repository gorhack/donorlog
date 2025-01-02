from unittest.mock import patch, AsyncMock

from fastapi import status

from apis.github import GithubOAuth
from tests.test_main import async_client_with_user, async_client


class TestGithubUsers:
    @patch.multiple(GithubOAuth,
                    verify_user_auth_token=AsyncMock(return_value=True),
                    get_user_monthly_sponsorship_amount=AsyncMock(return_value=42))
    async def test_get_github_user(self, async_client_with_user):
        response = await async_client_with_user.get("/users/gorhack")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "github_username": "gorhack",
            "github_monthly_sponsorship_amount": 42,
        }

    async def test_get_github_user_not_exist(self, async_client):
        response = await async_client.get("/users/not_a_user")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User does not exist or not verified."}
