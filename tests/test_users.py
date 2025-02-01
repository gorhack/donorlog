from datetime import datetime
from unittest.mock import patch, AsyncMock

from fastapi import status

from app.apis.github import GithubOAuth
from app.apis.opencollective import OpenCollectiveOAuth
from app.apis.utils import TotalAndMonthAmount
from tests.test_main import async_client_with_github_user, async_client, async_client_with_opencollective_user


class TestGithubUsers:
    @patch.multiple(GithubOAuth,
                    verify_user_auth_token=AsyncMock(return_value=True),
                    get_user_monthly_sponsorship_amount=AsyncMock(return_value=42))
    async def test_get_github_user(self, async_client_with_github_user):
        response = await async_client_with_github_user.get("/users/gorhack")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "github_username": "gorhack",
            "github_monthly_sponsorship_amount": 42,
            "opencollective": None
        }

    async def test_get_github_user_not_exist(self, async_client):
        response = await async_client.get("/users/not_a_user")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User does not exist or not verified."}

    @patch.multiple(GithubOAuth,
                    verify_user_auth_token=AsyncMock(return_value=True),
                    get_user_monthly_sponsorship_amount=AsyncMock(return_value=42))
    @patch.object(OpenCollectiveOAuth, "get_user_sponsorship_amount", return_value=TotalAndMonthAmount(
        month=10, total=42, last_checked=datetime.fromisoformat("2025-01-01T12:55:00Z")
    ))
    async def test_with_opencollective(self, mock_get_user_sponsorship_amount,
                                       async_client_with_opencollective_user):
        response = await async_client_with_opencollective_user.get("/users/gorhack")
        mock_get_user_sponsorship_amount.assert_called_once_with("opencollective_test_id")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "github_username": "gorhack",
            "github_monthly_sponsorship_amount": 42,
            "opencollective": {
                "last_checked": "2025-01-01T12:55:00Z",
                "month": 10,
                "total": 42,
            }
        }
