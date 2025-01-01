import json
import uuid
from unittest.mock import patch, AsyncMock

from fastapi import status
from fastapi.testclient import TestClient

from apis.github import GithubOAuth
from core.user_token import UserTokenId
from main import app, get_current_user, User, oauth2_scheme_no_error

client = TestClient(app)


class TestTemplates:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200
        # TODO improve testing for templates
        assert '''<input type="submit" value="Login with Github"''' in str(
            response.content
        )

    test_token: UserTokenId = None

    def override_oauth_token(self):
        yield self.test_token

    @patch.object(GithubOAuth, "verify_user_auth_token", return_value=True)
    def test_read_main_with_user(self, _):
        self.test_token = UserTokenId(user_id="1234", username="gorhack")
        app.dependency_overrides[oauth2_scheme_no_error] = self.override_oauth_token
        # TODO will need to override db, currently has gorhack hardcoded with an access token
        # could assert on mocked verify_user_auth_token
        response = client.get("/")
        assert response.status_code == 200
        assert """<p>Github username: gorhack</p>""" in str(response.content)


class TestGithubApi:
    @patch.multiple(
        GithubOAuth,
        verify_user_auth_token=AsyncMock(return_value=True),
        get_user_monthly_sponsorship_amount=AsyncMock(return_value="42"),
    )
    def test_get_github_search_overview(self):
        # TODO app.dependency_overrides[get_db_user] to override actual database user
        response = client.get("/search/gorhack")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "github_username": "gorhack",
            "github_monthly_sponsorship_amount": 42,
        }

    def test_post_github_search_redirect(self):
        response = client.post("/search", data={"github_username": "a_user"})
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.next.method == "GET"
        assert response.next.path_url == "/search/a_user"

    test_user: User = None

    def override_get_current_user(self):
        yield self.test_user

    def test_get_me(self):
        self.test_user = User(
            user_id=uuid.uuid4(),
            github_username="username",
            github_id=123,
            github_email="me@example.com",
            github_auth_token="auth-token",
        )
        app.dependency_overrides[get_current_user] = self.override_get_current_user
        response = client.get("/users/me")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == json.loads(self.test_user.json())


class TestSearchErrorHandling:
    def test_search_redirect_error(self):
        response = client.post("/search", data={"github_username": "not_a_user"})
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.next.method == "GET"
        assert response.next.path_url == "/search/not_a_user"
        response = client.get(response.next.path_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User not verified."}

    def test_get_search_error(self):
        # once there are multiple search options only error when all are empty
        response = client.get("/search/not_a_user")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User not verified."}
