from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


class TestTemplates:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200
        # TODO: improve testing for templates
        assert '''<input type="button" value="Login with Github"''' in str(
            response.content
        )

    def test_github_login(self):
        response = client.get("/?github_username=gorhack")
        assert response.status_code == 200
        assert """<p>Github username: gorhack</p>""" in str(response.content)

    def test_github_monthly_amount(self):
        response = client.get("/?github_monthly_sponsorship_amount=25")
        assert response.status_code == 200
        assert """<p>GitHub Monthly Amount: $25/mo</p>"""


class TestGithubApi:
    # TODO mock github oauth
    def test_github_username(self):
        response = client.post(
            "/search",
            data={
                "github_username": "gorhack",
                "github_monthly_sponsorship_amount": "23",
            },
        )
        assert response.status_code == 303
        assert (
            response.headers["location"]
            == "/search/gorhack?github_monthly_sponsorship_amount=23"
        )

    def test_get_github_username(self):
        response = client.get("/search/gorhack?github_monthly_sponsorship_amount=0")
        assert response.status_code == 200
        assert response.json() == {
            "github_username": "gorhack",
            "github_monthly_sponsorship_amount": 0,
        }


class TestSearchErrorHandling:
    def test_github_username_error(self):
        # once there are multiple search options only error when all are empty
        response = client.post("/search")
        assert response.status_code == 400
        assert response.json() == {"detail": "Github username must not be empty."}

    def test_get_search_error(self):
        # once there are multiple search options only error when all are empty
        response = client.get(
            "/search/gorhack", data={"github_monthly_sponsorship_amount": None}
        )
        assert response.status_code == 400
        assert response.json() == {
            "detail": "Must include valid github_monthly_sponsorship_amount query parameter."
        }
