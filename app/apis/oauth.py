from datetime import datetime
from typing import Optional

from app.apis.users.users_schema import TotalAndMonthAmount


def start_of_month() -> str:
    return datetime.today().strftime("%G-%m-01T00:00:01Z")


class OAuth:
    @staticmethod
    def login(state: str) -> str:
        raise NotImplementedError()

    @staticmethod
    async def get_access_token(code: str) -> str:
        raise NotImplementedError()

    @staticmethod
    async def get_id_and_username(access_token: str) -> (str, str):
        raise NotImplementedError()

    @staticmethod
    async def get_user_sponsorship_amount(access_token_or_id: str) -> Optional[TotalAndMonthAmount]:
        raise NotImplementedError()
