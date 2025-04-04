import re
from unittest.mock import patch

from fastapi import status

from app.apis.github import GithubAPI
from app.apis.opencollective import OpenCollectiveAPI
from app.apis.users.users_schema import SponsorNode
from tests.test_main import async_client, async_client_with_logged_in_user, add_users_to_database, \
    test_user_1_opencollective


class TestUserProfile:
    async def test_not_logged_in(self, async_client):
        response = await async_client.get("/profile")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(GithubAPI, "get_user_sponsorships_as_sponsor", return_value=[
        SponsorNode(user="user1", url="https://github.com/user1",
                    avatar_url="https://avatars.githubusercontent.com/u/26825299?v=4", total=1234),
        SponsorNode(user="user2", url="https://github.com/user2",
                    avatar_url="https://avatars.githubusercontent.com/u/26825299?v=4", total=1),
    ])
    @patch.object(OpenCollectiveAPI, "get_user_sponsorships_as_sponsor", return_value=[
        SponsorNode(user="user3", url="https://opencollective.com/user3",
                    avatar_url="https://images.opencollective.com/homebrew/362ae9d/logo.png", total=4567),
        SponsorNode(user="user4", url="https://opencollective.com/user4",
                    avatar_url="https://images.opencollective.com/core-js/92544a2/logo.png", total=789),
    ])
    async def test_user_profile(self, _gh, _oc, async_client_with_logged_in_user):
        await add_users_to_database([(test_user_1_opencollective, 1)])
        response = await async_client_with_logged_in_user.get("/profile")
        assert re.search((
            "<img src=\"https://images.opencollective.com/homebrew/362ae9d/logo.png\" alt=\"user3's Avatar\" width=\"25\" height=\"25\".*"
            "<a href=\"https://opencollective.com/user3\" target=\"_blank\">user3</a>.*"
            "<td>\\$45.67</td>.*"
            "<img src=\"https://avatars.githubusercontent.com/u/26825299\?v=4\" alt=\"user1's Avatar\" width=\"25\" height=\"25\".*"
            "<a href=\"https://github.com/user1\" target=\"_blank\">user1</a>.*"
            "<td>\\$12.34</td>.*"
            "<img src=\"https://images.opencollective.com/core-js/92544a2/logo.png\" alt=\"user4's Avatar\" width=\"25\" height=\"25\".*"
            "<a href=\"https://opencollective.com/user4\" target=\"_blank\">user4</a>.*"
            "<td>\\$7.89</td>.*"
            "<img src=\"https://avatars.githubusercontent.com/u/26825299\?v=4\" alt=\"user2's Avatar\" width=\"25\" height=\"25\">.*"
            "<a href=\"https://github.com/user2\" target=\"_blank\">user2</a>.*"
            "<td>\\$0.01</td>"
        ), response.text, re.DOTALL)

    @patch.object(GithubAPI, "get_user_sponsorships_as_sponsor", return_value=[])
    async def test_user_name_change_success(self, _, async_client_with_logged_in_user):
        response = await async_client_with_logged_in_user.post("/profile", data={"username": "test_update"})
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.next_request.method == "GET"
        response_redirect = await async_client_with_logged_in_user.get(response.next_request.url)
        assert "Updated username from test_user_1 to test_update." in response_redirect.text

    @patch.object(GithubAPI, "get_user_sponsorships_as_sponsor", return_value=[])
    async def test_user_name_change_failure(self, _, async_client_with_logged_in_user):
        await add_users_to_database([(test_user_1_opencollective, None)])
        response = await async_client_with_logged_in_user.post("/profile", data={"username": "test_oc_user_1"})
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.next_request.method == "GET"
        response_redirect = await async_client_with_logged_in_user.get(response.next_request.url)
        assert "Unable to update username to test_oc_user_1. Choose another." in response_redirect.text
