from unittest.mock import patch

from app.apis.github import GithubAPI
from app.apis.users.users_schema import SponsorNode
from tests.test_main import test_total_and_month, async_client, async_client_with_logged_in_user


class TestUserProfile:
    async def test_not_logged_in(self, async_client):
        response = await async_client.get("/profile")
        assert response.status_code == 401

    @patch.object(GithubAPI, "get_user_sponsorships_as_sponsor", return_value=[
        SponsorNode(user="user1", url="https://github.com/user1",
                    avatar_url="https://avatars.githubusercontent.com/u/26825299?v=4", total=1234),
        SponsorNode(user="user2", url="https://github.com/user2",
                    avatar_url="https://avatars.githubusercontent.com/u/26825299?v=4", total=1),
    ])
    async def test_user_profile(self, _, async_client_with_logged_in_user):
        response = await async_client_with_logged_in_user.get("/profile")
        assert "Welcome test_user_1" in response.text
        assert "<a href=\"https://github.com/user1\" target=\"_blank\">user1</a>" in response.text
        assert "<img src=\"https://avatars.githubusercontent.com/u/26825299?v=4\" alt=\"user1's Avatar\" width=\"25\" height=\"25\"" in response.text
        assert "<td>$12.34</td>" in response.text
        assert "<a href=\"https://github.com/user2\" target=\"_blank\">user2</a>" in response.text
        assert "<img src=\"https://avatars.githubusercontent.com/u/26825299?v=4\" alt=\"user2's Avatar\" width=\"25\" height=\"25\"" in response.text
        assert "<td>$0.01</td>" in response.text
