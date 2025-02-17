from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch, PropertyMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.apis.users.users_schema import GithubUser, OpencollectiveUser, User
from app.apis.utils import TotalAndMonthAmount
from app.core import migrate
from app.core.postgres import database
from app.main import app


@pytest.fixture
async def async_client():
    database.database_url = "postgresql://dl:dl@localhost:5555/donorlog_test"
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


test_user_1_github = GithubUser(github_id="gh_id_1", github_username="test_user_1",
                                github_auth_token="gh_a1")

test_user_1_opencollective = OpencollectiveUser(opencollective_id="oc_id_1",
                                                opencollective_username="test_oc_user_1")


async def add_users_to_database(user_userid: [(GithubUser | OpencollectiveUser, Optional[int])])->[User]:
    added_users = []
    # user[1] will have a valid user_id if that user is supposed to already exist
    for user in user_userid:
        if isinstance(user[0], OpencollectiveUser):
            added_users.append(await UsersModel().insert_or_update_opencollective_user(user[0], user[1]))

        if isinstance(user[0], GithubUser):
            added_users.append(await UsersModel().insert_or_update_github_user(user[0], user[1]))
    return added_users


@pytest.fixture
async def async_client_with_logged_in_user(async_client):
    await add_users_to_database([(test_user_1_github, None)])
    with patch("fastapi.Request.session", new_callable=PropertyMock, return_value={
        "session_id": "test_session_id",
        "token_expiry": (
                (datetime.now(timezone.utc) + timedelta(seconds=30)).replace(tzinfo=timezone.utc).timestamp()
        ),
        "username": test_user_1_github.github_username,
        "user_id": 1
    }):
        yield async_client  # schema is going to be dropped after test ends


TEST_TOTAL_AND_MONTH = TotalAndMonthAmount(
    month=1122,
    total=3344,
    last_checked=datetime.fromisoformat("2024-12-15T12:55:00Z")
)


class TestHome:
    async def test_get_home_unauthenticated(self, async_client):
        response = await async_client.get("/")
        assert response.status_code == 200
        # TODO improve testing for templates
        assert '''<input type="submit" value="Login with Github"''' in str(
            response.content
        )

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=TEST_TOTAL_AND_MONTH)
    async def test_get_home_database_authenticated(self, mock_get_user_sponsorship_amount,
                                                   async_client_with_logged_in_user):
        response = await async_client_with_logged_in_user.get("/")
        assert response.status_code == 200
        assert "<p>Username: test_user_1</p>" in response.text
        mock_get_user_sponsorship_amount.assert_called_once_with(test_user_1_github.github_auth_token)
        assert """Monthly Amount: $11.22""" in response.text
        assert """Total Amount: $33.44""" in response.text

    @patch("fastapi.Request.session", new_callable=PropertyMock, return_value={
            "session_id": "test_session_id",
            "token_expiry": (
                    (datetime.now(timezone.utc) + timedelta(seconds=30)).replace(tzinfo=timezone.utc).timestamp()
            ),
            "username": test_user_1_github.github_username,
            "user_id": 1
        })
    async def test_get_home_session_reset_with_bad_db_user(self, _, async_client):
        response = await async_client.get("/")
        assert response.status_code == 200
        assert '''<input type="submit" value="Login with Github"''' in str(
            response.content
        )

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=TEST_TOTAL_AND_MONTH)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=TEST_TOTAL_AND_MONTH)
    async def test_get_home_database_authenticated_with_opencollective(self, mock_get_user_sponsorship_amount, _,
                                                                       async_client_with_logged_in_user):
        await add_users_to_database([(test_user_1_opencollective, 1)])
        response = await async_client_with_logged_in_user.get("/")
        assert response.status_code == 200
        mock_get_user_sponsorship_amount.assert_called_once_with("oc_id_1")
        assert """<p>OpenCollective</p>""" in response.text
        assert """Total Amount: $66.88""" in response.text
        assert """Monthly Amount: $22.44""" in response.text
