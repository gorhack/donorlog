from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


class TestTemplates:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200
        # TODO: improve testing for templates
        assert """<form action="/search" method="post">""" in str(response.content)


class TestGithubApi:
    def test_github_username(self):
        response = client.post("/search", data={"github_username": "gorhack"})
        assert response.status_code == 200
        assert response.json() == {"github_username": "gorhack"}

    def test_get_github_username(self):
        response = client.get("/search?github_username=gorhack")
        assert response.status_code == 200
        assert response.json() == {"github_username": "gorhack"}


class TestSearchErrorHandling:
    def test_github_username_error(self):
        # once there are multiple search options only error when all are empty
        response = client.post("/search", data={"github_username": ""})
        assert response.status_code == 400
        assert response.json() == {"detail": "Github username must not be empty."}

    def test_get_search_error(self):
        # once there are multiple search options only error when all are empty
        response = client.get("/search?github_username=")
        assert response.status_code == 400
        assert response.json() == {
            "detail": "Must include github_username query parameter."
        }
