from typing import Optional

from asyncpg.pool import Pool

from app.apis.users.users_schema import User, OpencollectiveUser
from app.core.postgres import database
from users.users_schema import GithubUser


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
            "SELECT users.user_id, github_id, github_username, github_auth_token, opencollective_id, opencollective_username "
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
                    github_auth_token=user.get("github_auth_token"))
            if user.get("opencollective_id"):
                opencollective_user = OpencollectiveUser(
                    opencollective_id=user.get("opencollective_id"),
                    opencollective_username=user.get("opencollective_username"))

            return User(user_id=user.get("user_id"), username=username,
                        github_user=dict(github_user) if github_user else None,
                        opencollective_user=dict(opencollective_user) if opencollective_user else None)

    async def insert_or_update_github_user(self, github_user: GithubUser, user_id=None) -> Optional[User]:
        if not github_user:
            raise ValueError("Must provide a User to insert or update github user")

        async with database.pool.acquire() as connection:
            db_user_id = await self._lookup_user_id_by_external_id(connection, github_user.github_id)

            if not user_id and not db_user_id:
                # new user
                query = ("WITH CONFLICT_USERNAME AS ("
                         "    SELECT CONCAT($2::VARCHAR, '_', substr(md5(random()::TEXT), 1, 5)) as fixed_username FROM users WHERE username = $2)"
                         ", NEW_USER AS ("
                         "    INSERT INTO users (username) VALUES (COALESCE((SELECT fixed_username FROM CONFLICT_USERNAME), $2)) RETURNING user_id, username)"
                         "INSERT INTO github_users (github_id, github_username, github_auth_token, user_id)"
                         "  VALUES ($1, $2, $3, (SELECT user_id FROM NEW_USER)) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, github_user.github_id, github_user.github_username,
                    github_user.github_auth_token)
            elif user_id and db_user_id and user_id != db_user_id:
                # user already logged in, delete conflicting user and its other associated accounts
                await connection.execute("DELETE FROM users WHERE user_id = $1;", db_user_id)
                query = ("INSERT INTO github_users (github_id, github_username, github_auth_token, user_id)"
                         "  VALUES ($1, $2, $3, $4) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, github_user.github_id, github_user.github_username,
                    github_user.github_auth_token, user_id)
            else:
                # add or update GitHub user
                query = (
                    "INSERT INTO github_users (github_id, github_username, github_auth_token, user_id)"
                    "  VALUES ($1, $2, $3, COALESCE($4, (SELECT user_id FROM github_users WHERE github_id = $1::VARCHAR))) "
                    "ON CONFLICT (github_id) DO UPDATE SET "
                    "  github_username = excluded.github_username, "
                    "  github_auth_token = excluded.github_auth_token "
                    "RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, github_user.github_id, github_user.github_username,
                    github_user.github_auth_token, user_id)
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
                         "    SELECT CONCAT($2::VARCHAR, '_', substr(md5(random()::TEXT), 1, 5)) as fixed_username FROM users WHERE username = $2)"
                         ", NEW_USER AS ("
                         "    INSERT INTO users (username) VALUES (COALESCE((SELECT fixed_username FROM CONFLICT_USERNAME), $2)) RETURNING user_id, username)"
                         "INSERT INTO opencollective_users (opencollective_id, opencollective_username, user_id)"
                         "  VALUES ($1, $2, (SELECT user_id FROM NEW_USER)) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, opencollective_user.opencollective_id, opencollective_user.opencollective_username)
            elif user_id and db_user_id and user_id != db_user_id:
                # user already logged in, delete conflicting user and its other associated accounts
                await connection.execute("DELETE FROM users WHERE user_id = $1;", db_user_id)
                query = ("INSERT INTO opencollective_users (opencollective_id, opencollective_username, user_id)"
                         "  VALUES ($1, $2, $3) RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, opencollective_user.opencollective_id, opencollective_user.opencollective_username, user_id)
            else:
                # add or update GitHub user
                query = (
                    "INSERT INTO opencollective_users (opencollective_id, opencollective_username, user_id)"
                    "  VALUES ($1, $2, COALESCE($3, (SELECT user_id FROM opencollective_users WHERE opencollective_id = $1::VARCHAR))) "
                    "ON CONFLICT (opencollective_id) DO UPDATE SET "
                    "  opencollective_username = excluded.opencollective_username "
                    "RETURNING user_id;")
                new_user_id = await connection.fetchval(
                    query, opencollective_user.opencollective_id, opencollective_user.opencollective_username, user_id)
            db_username = await self._lookup_username_from_user_id(connection, new_user_id)
            if not new_user_id or not db_username:
                return None
            return User(user_id=new_user_id, username=db_username)
