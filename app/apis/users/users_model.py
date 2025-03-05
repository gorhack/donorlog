from typing import Optional

from asyncpg.pool import Pool

from app.apis.users.users_schema import User, OpencollectiveUser, GithubUser, TotalAndMonthAmount, RankedUsers, UserRank
from app.core.postgres import database


class UsersModel:
    @staticmethod
    async def _lookup_user_id_by_external_id(connection: Pool, external_id: str):
        if external_id is None:
            return None
        query = (
            "SELECT users.user_id FROM users "
            "   LEFT JOIN github_users ON github_users.user_id = users.user_id "
            "   LEFT JOIN opencollective_users ON opencollective_users.user_id = users.user_id "
            "WHERE github_id = $1 OR opencollective_id = $1;")
        return await connection.fetchval(query, external_id)

    @staticmethod
    async def _lookup_username_from_user_id(connection: Pool, user_id: str):
        return await connection.fetchval("SELECT username FROM users WHERE user_id = $1;", user_id)

    @staticmethod
    async def lookup_user_by_username(username: str) -> Optional[User]:
        if username is None:
            return None
        query = (
            "SELECT users.user_id, github_id, github_username, github_auth_token, "
            "  github_users.total_cents AS gh_total_cents , "
            "  github_users.month_cents AS gh_month_cents, "
            "  github_users.last_checked AS gh_last_checked, "
            "  opencollective_id, opencollective_username, "
            "  opencollective_users.total_cents AS oc_total_cents, "
            "  opencollective_users.month_cents AS oc_month_cents, "
            "  opencollective_users.last_checked AS oc_last_checked "
            "FROM users "
            "   LEFT JOIN github_users ON github_users.user_id = users.user_id "
            "   LEFT JOIN opencollective_users ON opencollective_users.user_id = users.user_id "
            "WHERE users.username = $1;"
        )
        async with database.pool.acquire() as connection:
            user = await connection.fetchrow(query, username)
            if user is None:
                return None
            github_user = None
            opencollective_user = None
            if user.get("github_id"):
                github_user = GithubUser(
                    github_id=user.get("github_id"),
                    github_username=user.get("github_username"),
                    github_auth_token=user.get("github_auth_token"),
                    amount=TotalAndMonthAmount(
                        total=user.get("gh_total_cents"),
                        month=user.get("gh_month_cents"),
                        last_checked=user.get("gh_last_checked")))
            if user.get("opencollective_id"):
                opencollective_user = OpencollectiveUser(
                    opencollective_id=user.get("opencollective_id"),
                    opencollective_username=user.get("opencollective_username"),
                    amount=TotalAndMonthAmount(
                        total=user.get("oc_total_cents"),
                        month=user.get("oc_month_cents"),
                        last_checked=user.get("oc_last_checked")))

            return User(user_id=user.get("user_id"), username=username,
                        github_user=github_user,
                        opencollective_user=opencollective_user)

    async def insert_or_update_github_user(self, github_user: GithubUser, user_id=None) -> Optional[User]:
        if not github_user:
            raise ValueError("Must provide a User to insert or update github user")

        async with database.pool.acquire() as connection:
            db_user_id = await self._lookup_user_id_by_external_id(connection, github_user.github_id)

            if not user_id and not db_user_id:
                # new user
                query = ("WITH CONFLICT_USERNAME AS ("
                         "  SELECT CONCAT($2::VARCHAR, '_', substr(md5(random()::TEXT), 1, 5)) as fixed_username FROM users WHERE username = $2"
                         "), NEW_USER AS ("
                         "  INSERT INTO users (username) VALUES "
                         "  ("
                         "    COALESCE((SELECT fixed_username FROM CONFLICT_USERNAME), $2)"
                         "  ) RETURNING user_id, username"
                         ")"
                         "INSERT INTO github_users ("
                         "  github_id, github_username, github_auth_token, user_id, total_cents, month_cents, last_checked"
                         ") VALUES ($1, $2, $3, (SELECT user_id FROM NEW_USER), $4, $5, $6) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, github_user.github_id, github_user.github_username,
                    github_user.github_auth_token, github_user.amount.total, github_user.amount.month,
                    github_user.amount.last_checked)
            elif user_id and db_user_id and user_id != db_user_id:
                # user already logged in, delete conflicting user and its other associated accounts
                await connection.execute("DELETE FROM users WHERE user_id = $1;", db_user_id)
                query = ("INSERT INTO github_users "
                         "("
                         "  github_id, github_username, github_auth_token, user_id, total_cents, month_cents, last_checked"
                         ") VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, github_user.github_id, github_user.github_username,
                    github_user.github_auth_token, user_id, github_user.amount.total, github_user.amount.month,
                    github_user.amount.last_checked)
            else:
                # add or update GitHub user
                query = (
                    "INSERT INTO github_users "
                    "("
                    "  github_id, github_username, github_auth_token, user_id, total_cents, month_cents, last_checked"
                    ") VALUES ("
                    "  $1, $2, $3, COALESCE($4, (SELECT user_id FROM github_users WHERE github_id = $1::VARCHAR)), $5, "
                    "$6, $7"
                    ") ON CONFLICT (github_id) DO UPDATE SET "
                    "  github_username = excluded.github_username, "
                    "  github_auth_token = excluded.github_auth_token "
                    "RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, github_user.github_id, github_user.github_username,
                    github_user.github_auth_token, user_id, github_user.amount.total, github_user.amount.month,
                    github_user.amount.last_checked)
            db_username = await self._lookup_username_from_user_id(connection, new_user_id)
            if not new_user_id or not db_username:
                return None
            return User(user_id=new_user_id, username=db_username)

    async def insert_or_update_opencollective_user(self, opencollective_user: OpencollectiveUser, user_id=None) -> \
            Optional[User]:
        if not opencollective_user:
            raise ValueError("Must provide a User to insert or update open collective user")

        async with database.pool.acquire() as connection:
            db_user_id = await self._lookup_user_id_by_external_id(connection, opencollective_user.opencollective_id)

            if not user_id and not db_user_id:
                # new user
                query = ("WITH CONFLICT_USERNAME AS ("
                         "  SELECT CONCAT($2::VARCHAR, '_', substr(md5(random()::TEXT), 1, 5)) as fixed_username FROM users WHERE username = $2"
                         "), NEW_USER AS ("
                         "  INSERT INTO users (username) VALUES "
                         "  ("
                         "    COALESCE((SELECT fixed_username FROM CONFLICT_USERNAME), $2)"
                         "  ) RETURNING user_id, username"
                         ")"
                         "INSERT INTO opencollective_users "
                         "("
                         "  opencollective_id, opencollective_username, user_id, total_cents, month_cents, last_checked"
                         ") VALUES ($1, $2, (SELECT user_id FROM NEW_USER), $3, $4, $5) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, opencollective_user.opencollective_id, opencollective_user.opencollective_username,
                    opencollective_user.amount.total, opencollective_user.amount.month,
                    opencollective_user.amount.last_checked)
            elif user_id and db_user_id and user_id != db_user_id:
                # user already logged in, delete conflicting user and its other associated accounts
                await connection.execute("DELETE FROM users WHERE user_id = $1;", db_user_id)
                query = ("INSERT INTO opencollective_users "
                         "("
                         "  opencollective_id, opencollective_username, user_id, total_cents, month_cents, last_checked"
                         ") VALUES ($1, $2, $3, $4, $5, $6) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, opencollective_user.opencollective_id, opencollective_user.opencollective_username, user_id,
                    opencollective_user.amount.total, opencollective_user.amount.month,
                    opencollective_user.amount.last_checked)
            else:
                # add or update GitHub user
                query = (
                    "INSERT INTO opencollective_users "
                    "("
                    "  opencollective_id, opencollective_username, user_id, total_cents, month_cents, last_checked"
                    ") VALUES ("
                    "  $1, $2, COALESCE($3, (SELECT user_id FROM opencollective_users WHERE opencollective_id = $1::VARCHAR)),"
                    "  $4, $5, $6"
                    ") ON CONFLICT (opencollective_id) DO UPDATE SET "
                    "  opencollective_username = excluded.opencollective_username "
                    "RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, opencollective_user.opencollective_id, opencollective_user.opencollective_username, user_id,
                    opencollective_user.amount.total, opencollective_user.amount.month,
                    opencollective_user.amount.last_checked)
            db_username = await self._lookup_username_from_user_id(connection, new_user_id)
            if not new_user_id or not db_username:
                return None
            return User(user_id=new_user_id, username=db_username)

    @staticmethod
    async def update_github_total_month(github_user: GithubUser, user_id: int):
        if not github_user:
            raise ValueError("Must provide an GitHub User to update amounts")
        async with database.pool.acquire() as connection:
            query = (
                "UPDATE github_users SET total_cents = $1, month_cents = $2, last_checked = $3 WHERE user_id = $4;"
            )
            await connection.execute(query, github_user.amount.total, github_user.amount.month,
                                     github_user.amount.last_checked, user_id)

    @staticmethod
    async def update_opencollective_total_month(opencollective_user: OpencollectiveUser, user_id: int):
        if not opencollective_user:
            raise ValueError("Must provide an OpenCollective User to update amounts")
        async with database.pool.acquire() as connection:
            query = (
                "UPDATE opencollective_users SET total_cents = $1, month_cents = $2, last_checked = $3 WHERE user_id = $4;"
            )
            await connection.execute(query, opencollective_user.amount.total, opencollective_user.amount.month,
                                     opencollective_user.amount.last_checked, user_id)

    @staticmethod
    async def ranked_totals(max_num: int = 10) -> list[RankedUsers]:
        users = []
        async with database.pool.acquire() as connection:
            results = await connection.fetch(
                "SELECT total_rank, username, total_cents FROM ranked_users_view ORDER BY total_rank, username LIMIT $1;",
                max_num)
            for row in results:
                users.append(RankedUsers(rank=row.get("total_rank"), username=row.get("username"),
                                         amount=row.get("total_cents")))
        return users

    @staticmethod
    async def ranked_months(max_num: int = 10) -> list[RankedUsers]:
        users = []
        async with database.pool.acquire() as connection:
            results = await connection.fetch(
                "SELECT month_rank, username, month_cents FROM ranked_users_view ORDER BY month_rank, username LIMIT $1;",
                max_num)
            for row in results:
                users.append(RankedUsers(rank=row.get("month_rank"), username=row.get("username"),
                                         amount=row.get("month_cents")))
        return users

    @staticmethod
    async def update_ranked_users_view():
        async with database.pool.acquire() as connection:
            await connection.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY ranked_users_view;")

    @staticmethod
    async def ranking_for_amount(month_amount: int, total_amount: int) -> UserRank:
        if total_amount is None or month_amount is None:
            return UserRank(total_rank=-1, month_rank=-1, total=-1)
        async with database.pool.acquire() as connection:
            result = await connection.fetchrow("""
                SELECT 1 + coalesce((SELECT ranked_users_view.month_rank
                     FROM ranked_users_view
                     WHERE ranked_users_view.month_cents > $1
                     ORDER BY ranked_users_view.month_rank DESC
                     LIMIT 1), 0) AS month_rank,
                1 + coalesce((SELECT ranked_users_view.total_rank
                     FROM ranked_users_view
                     WHERE ranked_users_view.total_cents > $2
                     ORDER BY ranked_users_view.total_rank DESC
                     LIMIT 1), 0) AS total_rank,
                (SELECT total_rank FROM ranked_users_view ORDER BY total_rank DESC LIMIT 1) AS total;""",
                                               month_amount, total_amount)
            return UserRank(total_rank=result.get("total_rank"), month_rank=result.get("month_rank"),
                            total=result.get("total"))
