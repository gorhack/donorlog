from datetime import datetime, timezone, timedelta
from unittest.mock import patch, PropertyMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.apis.github import GithubOAuth
from app.core import migrate
from app.core.postgres import database
from app.main import app


@pytest.fixture
async def async_client():
    # TODO change RDS_DATABASE_URL for tests
    await database.connect()
    query = """
        DROP SCHEMA IF EXISTS public CASCADE;
        CREATE SCHEMA IF NOT EXISTS public;
    """
    async with database.pool.acquire() as connection:
        await connection.execute(query)
    await migrate.apply_pending_migrations()

    async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    async with database.pool.acquire() as connection:
        await connection.execute("DROP SCHEMA IF EXISTS public CASCADE;")
    await database.disconnect()


@pytest.fixture
async def async_client_with_user(async_client):
    async with database.pool.acquire() as connection:
        await connection.execute("INSERT INTO users (email, github_username, github_auth_token) VALUES ($1, $2, $3)",
                                 "kyle@example.com", "gorhack", "test_access_token")
    with patch("fastapi.Request.session", new_callable=PropertyMock, return_value={
        "session_id": "test_session_id",
        "token_expiry": (
                (datetime.now(timezone.utc) + timedelta(seconds=30)).replace(tzinfo=timezone.utc).timestamp()
        ),
        "username": "gorhack"
    }):
        yield async_client  # schema is going to be dropped after test ends


class TestHome:
    async def test_get_home_unauthenticated(self, async_client):
        response = await async_client.get("/")
        assert response.status_code == 200
        # TODO improve testing for templates
        assert '''<input type="submit" value="Login with Github"''' in str(
            response.content
        )

    @patch.object(GithubOAuth, "get_user_monthly_sponsorship_amount", return_value=42)
    async def test_get_home_database_authenticated(self, mock_get_user_monthly_sponsorship_amount,
                                                   async_client_with_user):
        response = await async_client_with_user.get("/")
        assert response.status_code == 200
        assert """<p>GitHub username: gorhack</p>""" in response.text
        mock_get_user_monthly_sponsorship_amount.assert_called_once_with(
            access_token="test_access_token",
            username="gorhack"
        )
