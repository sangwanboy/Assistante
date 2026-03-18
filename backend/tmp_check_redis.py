from app.services.redis_client import RedisClient
import asyncio

async def check():
    r = RedisClient()
    await r.connect()
    print("Redis available:", r.available)

if __name__ == "__main__":
    asyncio.run(check())

