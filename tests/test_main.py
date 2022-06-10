from unittest.mock import patch, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from apis.github import GithubOAuth
from ..main import app, get_current_user, User

client = TestClient(app)


class TestTemplates:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200
        # TODO: improve testing for templates
        assert '''<input type="submit" value="Login with Github"''' in str(
            response.content
        )

    some_user = User(
        github_username="gorhack",
        github_id=123456,
        github_email="gorhack@example.com",
        github_auth_token="my-valid-oauth-token",
    )

    async def override_get_current_user(self):
        return self.some_user

    @patch.object(GithubOAuth, "get_user_monthly_sponsorship_amount")
    def test_github_login(self, mock_method: MagicMock):
        app.dependency_overrides[get_current_user] = self.override_get_current_user
        response = client.get("/")
        assert mock_method.call_args.args[0] is self.some_user.github_auth_token
        assert mock_method.call_args.args[1] is self.some_user.github_username
        assert response.status_code == 200
        assert """<p>Github username: gorhack</p>""" in str(response.content)


class TestGithubApi:
    def test_get_github_username(self):
        response = client.get("/search/gorhack")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "detail": "User not found.",
        }


class TestSearchErrorHandling:
    def test_github_username_error(self):
        # must provide a username
        response = client.post("/search")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not Found"}

    def test_get_search_error(self):
        # once there are multiple search options only error when all are empty
        response = client.get("/search/gorhack")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User not found."}
