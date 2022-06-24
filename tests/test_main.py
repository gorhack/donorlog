from unittest.mock import patch, AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from apis.github import GithubOAuth
from ..main import app

client = TestClient(app)


class TestTemplates:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200
        # TODO: improve testing for templates
        assert '''<input type="submit" value="Login with Github"''' in str(
            response.content
        )


class TestGithubApi:
    @pytest.mark.asyncio
    @patch.multiple(
        GithubOAuth,
        verify_user_auth_token=AsyncMock(return_value=True),
        get_user_monthly_sponsorship_amount=AsyncMock(return_value="42"),
    )
    async def test_get_github_search_overview(self):
        # TODO app.dependency_overrides[get_db_user] to override actual database user
        response = client.get("/search/gorhack")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "github_username": "gorhack",
            "github_monthly_sponsorship_amount": 42,
        }


class TestSearchErrorHandling:
    def test_github_username_error(self):
        # must provide a username
        response = client.post("/search")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

    def test_get_search_error(self):
        # once there are multiple search options only error when all are empty
        response = client.get("/search/not_a_user")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User not verified."}
