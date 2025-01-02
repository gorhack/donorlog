from postgres import database
from users import users_schema
from users.users_schema import User


async def insert_user_or_update_auth_token(user: users_schema.User):
    if user and await lookup_by_github_username(user.github_username):
        query = "UPDATE users SET github_auth_token = $3 WHERE email = $1 AND github_username = $2"
    else:
        query = "INSERT INTO users (email, github_username, github_auth_token) VALUES ($1, $2, $3)"
    async with database.pool.acquire() as connection:
        await connection.execute(query, user.email, user.github_username, user.github_auth_token)


async def lookup_by_github_username(username: str) -> users_schema.User | None:
    query = "SELECT * FROM users WHERE github_username = $1;"
    async with database.pool.acquire() as connection:
        user = await connection.fetchrow(query,  username)
        if user is not None:
            return User(
                email=user["email"],
                github_username=user["github_username"],
                github_auth_token=user["github_auth_token"], )
        else:
            return None
