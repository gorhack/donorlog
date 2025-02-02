from app.apis.users import users_schema
from app.apis.users.users_schema import User
from app.core.postgres import database


async def insert_user_or_update_auth_token(user: users_schema.User):
    if user and await lookup_by_github_username(user.github_username):
        query = "UPDATE users SET github_auth_token = $2 WHERE github_username = $1"
    else:
        query = "INSERT INTO users (github_username, github_auth_token) VALUES ($1, $2)"
    async with database.pool.acquire() as connection:
        await connection.execute(query, user.github_username, user.github_auth_token)


async def lookup_by_github_username(username: str) -> users_schema.User | None:
    query = "SELECT * FROM users WHERE github_username = $1;"
    async with database.pool.acquire() as connection:
        user = await connection.fetchrow(query, username)
        if user is not None:
            return User(
                github_username=user["github_username"],
                github_auth_token=user["github_auth_token"],
                opencollective_id=user["opencollective_id"])
        else:
            return None


async def add_opencollective_id_to_user(github_username: str, opencollective_id: str):
    query = "UPDATE users SET opencollective_id = $1 WHERE github_username = $2;"
    async with database.pool.acquire() as connection:
        # TODO return bool with True if response is "UPDATE 1" or false if failed to update
        await connection.execute(query, opencollective_id, github_username)
