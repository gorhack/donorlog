from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import status

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_model import UsersModel
from app.apis.users.users_schema import GithubUser, OpencollectiveUser
from app.apis.users.users_schema import TotalAndMonthAmount
from tests.test_main import add_users_to_database, test_user_1_github, test_user_1_opencollective, async_client, \
    test_total_and_month


class TestGithubUsers:
    @patch.object(GithubAPI, "get_user_sponsorship_amount",
                  return_value=TotalAndMonthAmount(month=10, total=15,
                                                   last_checked=datetime.fromisoformat(
                                                       "2070-12-12T00:01:00Z")))
    async def test_get_github_user(self, mock_get_user_sponsorship_amount, async_client):
        await add_users_to_database([(test_user_1_github, None)])
        default_user = await UsersModel.lookup_user_by_username("test_user_1")
        assert default_user.github_user.amount.month == 1122
        assert default_user.github_user.amount.total == 3344
        assert default_user.github_user.amount.last_checked == datetime.fromisoformat("2025-01-01T00:01:45Z")
        response = await async_client.get("/users/test_user_1")
        assert response.status_code == status.HTTP_200_OK
        mock_get_user_sponsorship_amount.assert_called_once_with(test_user_1_github.github_auth_token)
        assert response.json() == {
            "username": "test_user_1",
            "github": {
                "last_checked": "2070-12-12T00:01:00Z",
                "month": 10,
                "total": 15,
            },
            "opencollective": None
        }
        updated_user = await UsersModel.lookup_user_by_username("test_user_1")
        assert updated_user.github_user.amount.month == 10
        assert updated_user.github_user.amount.total == 15
        assert updated_user.github_user.amount.last_checked == datetime.fromisoformat("2070-12-12T00:01:00Z")

    async def test_get_github_user_not_exist(self, async_client):
        response = await async_client.get("/users/not_a_user")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User does not exist or not verified."}

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=TotalAndMonthAmount(
        month=10, total=42, last_checked=datetime.fromisoformat("2025-01-01 12:55:00+00:00")
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
                "last_checked": "2025-01-01T00:01:45Z",
                "month": 1122,
                "total": 3344,
            },
            "opencollective": {
                "last_checked": "2025-01-01T12:55:00Z",
                "month": 10,
                "total": 42,
            }
        }

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    async def test_github_oc_conflict(self, _, _1, async_client):
        users = await add_users_to_database([(test_user_1_github, None), (test_user_1_opencollective, None)])
        assert len(users) == 2 and users[0].username == test_user_1_github.github_username and users[
            1].username == test_user_1_opencollective.opencollective_username
        response = await async_client.get("/users/test_oc_user_1")
        assert response.status_code == status.HTTP_200_OK

        conflict_user = await add_users_to_database([(test_user_1_opencollective, 1)])
        assert conflict_user[0].username == users[0].username
        response = await async_client.get("/users/test_oc_user_1")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_duplicate_username(self, async_client):
        github_conflict = GithubUser(github_username=test_user_1_github.github_username, github_id="somethingelse",
                                     github_auth_token="gh_auth", amount=test_total_and_month)
        added_users = await add_users_to_database([(test_user_1_github, None), (github_conflict, None)])
        assert len(added_users) == 2
        assert added_users[0].username == test_user_1_github.github_username
        assert added_users[0].username < added_users[1].username
        assert len(added_users[1].username) == len(added_users[0].username) + 6

    @patch.object(GithubAPI, "get_user_sponsorship_amount")
    async def test_user_no_lookup_because_of_date(self, mock_get_user_sponsorship_amount, async_client):
        await add_users_to_database([
            (GithubUser(github_id="gh_id_1",
                        github_username="test_user_1",
                        github_auth_token="gh_a1",
                        amount=TotalAndMonthAmount(
                            month=1122,
                            total=3344,
                            last_checked=datetime.now(tz=timezone.utc)))
             , None)])
        response = await async_client.get("/users/test_user_1")
        assert response.status_code == status.HTTP_200_OK
        assert not mock_get_user_sponsorship_amount.called


class TestOpenCollectiveUsers:
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount",
                  return_value=TotalAndMonthAmount(month=10, total=15,
                                                   last_checked=datetime.fromisoformat(
                                                       "2070-12-12T00:01:00Z")))
    async def test_get_opencollective_user(self, mock_get_user_sponsorship_amount, async_client):
        await add_users_to_database([(test_user_1_opencollective, None)])
        default_user = await UsersModel.lookup_user_by_username("test_oc_user_1")
        assert default_user.opencollective_user.amount.month == 1122
        assert default_user.opencollective_user.amount.total == 3344
        assert default_user.opencollective_user.amount.last_checked == datetime.fromisoformat("2025-01-01T00:01:45Z")
        response = await async_client.get("/users/test_oc_user_1")
        assert response.status_code == status.HTTP_200_OK
        mock_get_user_sponsorship_amount.assert_called_once_with(test_user_1_opencollective.opencollective_id)
        assert response.json() == {
            "username": "test_oc_user_1",
            "opencollective": {
                "last_checked": "2070-12-12T00:01:00Z",
                "month": 10,
                "total": 15,
            },
            "github": None
        }
        updated_user = await UsersModel.lookup_user_by_username("test_oc_user_1")
        assert updated_user.opencollective_user.amount.month == 10
        assert updated_user.opencollective_user.amount.total == 15
        assert updated_user.opencollective_user.amount.last_checked == datetime.fromisoformat("2070-12-12T00:01:00Z")

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=TotalAndMonthAmount(
        month=10, total=42, last_checked=datetime.fromisoformat("2025-01-01T12:55:00Z")
    ))
    async def test_with_opencollective(self, _, mock_gh_get_user_sponsorship_amount,
                                       async_client):
        await add_users_to_database([(test_user_1_opencollective, None), (test_user_1_github, 1)])
        response = await async_client.get("/users/test_oc_user_1")
        mock_gh_get_user_sponsorship_amount.assert_called_once_with("gh_a1")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "username": "test_oc_user_1",
            "github": {
                "last_checked": "2025-01-01T00:01:45Z",
                "month": 1122,
                "total": 3344,
            },
            "opencollective": {
                "last_checked": "2025-01-01T12:55:00Z",
                "month": 10,
                "total": 42,
            }
        }

    @patch.object(GithubAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount", return_value=test_total_and_month)
    async def test_oc_github_conflict(self, _, _1, async_client):
        users = await add_users_to_database([(test_user_1_opencollective, None), (test_user_1_github, None)])
        assert len(users) == 2 and users[0].username == test_user_1_opencollective.opencollective_username and users[
            1].username == test_user_1_github.github_username
        response = await async_client.get("/users/test_user_1")
        assert response.status_code == status.HTTP_200_OK

        conflict_user = await add_users_to_database([(test_user_1_github, 1)])
        assert conflict_user[0].username == users[0].username
        response = await async_client.get("/users/test_user_1")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_duplicate_username(self, async_client):
        oc_conflict = OpencollectiveUser(opencollective_username=test_user_1_opencollective.opencollective_username,
                                         opencollective_id="somethingelse", amount=test_total_and_month)
        added_users = await add_users_to_database([(test_user_1_opencollective, None), (oc_conflict, None)])
        assert len(added_users) == 2
        assert added_users[0].username == test_user_1_opencollective.opencollective_username
        assert added_users[0].username < added_users[1].username
        assert len(added_users[1].username) == len(added_users[0].username) + 6

    @patch.object(OpenCollectiveAPI, "get_user_sponsorship_amount")
    async def test_user_no_lookup_because_of_date(self, mock_get_user_sponsorship_amount, async_client):
        await add_users_to_database([
            (OpencollectiveUser(opencollective_id="oc_id_1",
                                opencollective_username="test_oc_user_1",
                                amount=TotalAndMonthAmount(
                                    month=1122,
                                    total=3344,
                                    last_checked=datetime.now(tz=timezone.utc), ))
             , None)])
        response = await async_client.get("/users/test_oc_user_1")
        assert response.status_code == status.HTTP_200_OK
        assert not mock_get_user_sponsorship_amount.called
