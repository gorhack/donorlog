import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch, PropertyMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.apis.users.users_schema import GithubUser, OpencollectiveUser, User, TotalAndMonthAmount
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


async def add_users_to_database(user_userid: [(GithubUser | OpencollectiveUser, Optional[int])]) -> [User]:
    added_users = []
    # user[1] will have a valid user_id if that user is supposed to already exist
    for user in user_userid:
        if isinstance(user[0], OpencollectiveUser):
            added_users.append(await UsersModel().insert_or_update_opencollective_user(user[0], user[1]))

        if isinstance(user[0], GithubUser):
            added_users.append(await UsersModel().insert_or_update_github_user(user[0], user[1]))
    return added_users


test_total_and_month = TotalAndMonthAmount(
    month=1122,
    total=3344,
    last_checked=datetime.fromisoformat("2025-01-01 00:01:45+00:00")
)

test_user_1_github = GithubUser(github_id="gh_id_1",
                                github_username="test_user_1",
                                github_auth_token="gh_a1",
                                amount=test_total_and_month)

test_user_1_opencollective = OpencollectiveUser(opencollective_id="oc_id_1",
                                                opencollective_username="test_oc_user_1",
                                                amount=test_total_and_month)


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


class TestHome:
    async def test_get_home_unauthenticated(self, async_client):
        response = await async_client.get("/")
        assert response.status_code == 200
        # TODO improve testing for templates
        assert "Login with GitHub" in response.text
        assert "Login with OpenCollective" in response.text

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    async def test_get_home_github_user(self, mock_get_user_sponsorship_amount,
                                        async_client_with_logged_in_user):
        response = await async_client_with_logged_in_user.get("/")
        assert response.status_code == 200
        assert "Username: test_user_1" in response.text
        mock_get_user_sponsorship_amount.assert_called_once_with(test_user_1_github.github_auth_token)
        assert "Monthly Amount: $11.22" in response.text
        assert "Total Amount: $33.44" in response.text
        assert "Last Updated: Jan 01, 25" in response.text
        assert "Link OpenCollective" in response.text
        assert "Linked GitHub" in response.text

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
        assert "Login with GitHub" in response.text
        assert "Login with OpenCollective" in response.text

    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    @patch("fastapi.Request.session", new_callable=PropertyMock, return_value={
        "session_id": "test_session_id",
        "token_expiry": (
                (datetime.now(timezone.utc) + timedelta(seconds=30)).replace(tzinfo=timezone.utc).timestamp()
        ),
        "username": test_user_1_opencollective.opencollective_username,
        "user_id": 1
    })
    async def test_get_home_opencollective_user(self, _, mock_get_user_sponsorship_amount,
                                                async_client):
        await add_users_to_database([(test_user_1_opencollective, None)])
        response = await async_client.get("/")
        assert response.status_code == 200
        assert "Username: test_oc_user_1" in response.text
        mock_get_user_sponsorship_amount.assert_called_once_with(test_user_1_opencollective.opencollective_id)
        assert "Monthly Amount: $11.22" in response.text
        assert "Total Amount: $33.44" in response.text
        assert "Last Updated: Jan 01, 25" in response.text
        assert "Link GitHub" in response.text
        assert "Linked OpenCollective" in response.text

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount")
    async def test_get_home_github_and_opencollective(self, mock_oc_get_user_sponsorship_amount, _,
                                                      async_client_with_logged_in_user):
        update_oc_date = copy.deepcopy(test_user_1_opencollective)
        update_oc_date.amount.last_checked = datetime.fromisoformat("2025-01-05 00:01:45+00:00")
        await add_users_to_database([(update_oc_date, 1)])
        mock_oc_get_user_sponsorship_amount.return_value = update_oc_date.amount
        response = await async_client_with_logged_in_user.get("/")
        assert response.status_code == 200
        mock_oc_get_user_sponsorship_amount.assert_called_once_with("oc_id_1")
        assert "Linked OpenCollective" in response.text
        assert "Linked GitHub" in response.text
        assert "Total Amount: $66.88" in response.text
        assert "Monthly Amount: $22.44" in response.text
        assert "Last Updated: Jan 05, 25" in response.text

    async def test_ranked_totals(self, async_client):
        user1 = copy.deepcopy(test_user_1_github)
        user1.amount.total = 1000
        user1.github_username = user1.github_id = "user1_1000"

        user2_oc = copy.deepcopy(test_user_1_opencollective)
        user2_oc.amount.total = 500
        user2_oc.opencollective_username = user2_oc.opencollective_id = "user2_999"
        user2_gh = copy.deepcopy(test_user_1_github)
        user2_gh.amount.total = 499
        user2_gh.github_id = "user2_999"

        user2_3 = copy.deepcopy(test_user_1_opencollective)
        user2_3.amount.total = 999
        user2_3.opencollective_username = user2_3.opencollective_id = "user2_oc_only_999"

        user2_3_oc = copy.deepcopy(test_user_1_opencollective)
        user2_3_oc.amount.total = 499
        user2_3_oc.opencollective_id = "user_2_3_999"
        user2_3_gh = copy.deepcopy(test_user_1_github)
        user2_3_gh.amount.total = 500
        user2_3_gh.github_username = user2_3_gh.github_id = "user_2_3_999"

        user5 = copy.deepcopy(test_user_1_github)
        user5.amount.total = 998
        user5.github_username = user5.github_id = "user5_998"

        user6 = copy.deepcopy(test_user_1_opencollective)
        user6.amount.total = 997
        user6.opencollective_username = user6.opencollective_id = "user6_997"

        user7 = copy.deepcopy(test_user_1_github)
        user7.amount.total = 996
        user7.github_username = user7.github_id = "user7_996"

        user8 = copy.deepcopy(test_user_1_opencollective)
        user8.amount.total = 900
        user8.opencollective_username = user8.opencollective_id = "user8_900"

        user9 = copy.deepcopy(test_user_1_github)
        user9.amount.total = 800
        user9.github_username = user9.github_id = "user9_800"

        user10_oc = copy.deepcopy(test_user_1_opencollective)
        user10_oc.amount.total = 798
        user10_oc.opencollective_id = "user10_799"
        user10_gh = copy.deepcopy(test_user_1_github)
        user10_gh.amount.total = 1
        user10_gh.github_username = user10_gh.github_id = "user10_799"

        user11 = copy.deepcopy(test_user_1_github)
        user11.amount.total = 798
        user11.github_username = user11.github_id = "user11_798"

        await add_users_to_database(
            [(user10_oc, None), (user10_gh, 1), (user2_oc, None), (user2_gh, 2), (user2_3_gh, None), (user2_3_oc, 3),
             (user2_3, None), (user11, None), (user9, None), (user5, None), (user8, None), (user6, None), (user7, None),
             (user1, None)])
        response = await async_client.get("/")
        assert re.search((
                   "<td>user1_1000</td>.*"
                   "<td>user2_999</td>.*"
                   "<td>user2_oc_only_999</td>.*"
                   "<td>user_2_3_999</td>.*"
                   "<td>user5_998</td>.*"
                   "<td>user6_997</td>.*"
                   "<td>user7_996</td>.*"
                   "<td>user8_900</td>.*"
                   "<td>user9_800</td>.*"
                   "<td>user10_799</td>"
               ), response.text, re.DOTALL)
        assert "user11_798" not in response.text
