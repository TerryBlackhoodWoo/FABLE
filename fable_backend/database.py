from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import MONGODB_URI, DB_NAME

_client: AsyncIOMotorClient | None = None


def connect():
    global _client
    _client = AsyncIOMotorClient(MONGODB_URI)


def close():
    if _client:
        _client.close()


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError(
            "DB가 아직 연결되지 않았습니다. connect()를 먼저 호출하세요."
        )
    return _client[DB_NAME]
