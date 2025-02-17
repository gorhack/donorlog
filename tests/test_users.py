from datetime import datetime
from unittest.mock import patch

from fastapi import status

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.utils import TotalAndMonthAmount
from tests.test_main import add_users_to_database, test_user_1_github, test_user_1_opencollective
from tests.test_main import async_client, TEST_TOTAL_AND_MONTH


class TestGithubUsers:
    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=TEST_TOTAL_AND_MONTH)
    async def test_get_github_user(self, mock_get_user_sponsorship_amount, async_client):
        await add_users_to_database([(test_user_1_github, None)])
        response = await async_client.get("/users/test_user_1")
        assert response.status_code == status.HTTP_200_OK
        mock_get_user_sponsorship_amount.assert_called_once_with(test_user_1_github.github_auth_token)
        assert response.json() == {
            "username": "test_user_1",
            "github": {
                "last_checked": "2024-12-15T12:55:00Z",
                "month": 1122,
                "total": 3344,
            },
            "opencollective": None
        }

    async def test_get_github_user_not_exist(self, async_client):
        response = await async_client.get("/users/not_a_user")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User does not exist or not verified."}

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=TEST_TOTAL_AND_MONTH)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=TotalAndMonthAmount(
        month=10, total=42, last_checked=datetime.fromisoformat("2025-01-01T12:55:00Z")
    ))
    async def test_with_opencollective(self, mock_oc_get_user_sponsorship_amount, _,
                                       async_client):
        await add_users_to_database([(test_user_1_github, None), (test_user_1_opencollective, 1)])
        response = await async_client.get("/users/test_user_1")
        mock_oc_get_user_sponsorship_amount.assert_called_once_with("oc_id_1")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "username": "test_user_1",
            "github": {
                "last_checked": "2024-12-15T12:55:00Z",
                "month": 1122,
                "total": 3344,
            },
            "opencollective": {
                "last_checked": "2025-01-01T12:55:00Z",
                "month": 10,
                "total": 42,
            }
        }
