import asyncpg

from config import settings

DATABASE_URL = settings.DATABASE_URL


class Postgres:
    def __init__(self, database_url: str):
        self.pool = None
        self.database_url = database_url

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.database_url)

    async def disconnect(self):
        self.pool.close()


database = Postgres(DATABASE_URL)
