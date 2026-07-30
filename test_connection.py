"""
MongoDB Atlas 연결 테스트 스크립트 (motor async 드라이버 사용)

사용법:
1. 이 파일과 같은 폴더에 .env 파일 위치 (Atlas에서 다운받은 파일)
2. .env 안에 MONGODB_URI= 형태로 연결 문자열이 있는지 확인
   (없다면 아래 안내대로 직접 추가)
3. pip install python-dotenv motor
4. python test_connection.py
"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()  # .env 파일 읽어서 환경변수로 로드

MONGODB_URI = os.getenv("MONGODB_URI")  # .env의 키 이름이 다르면 여기 수정


async def test_connection():
    if not MONGODB_URI:
        print("❌ MONGODB_URI를 찾을 수 없습니다. .env 파일의 키 이름을 확인하세요.")
        return

    client = AsyncIOMotorClient(MONGODB_URI)
    try:
        # ping으로 연결 확인 (실제 쿼리 없이 서버 응답만 체크)
        await client.admin.command("ping")
        print("✅ MongoDB Atlas 연결 성공!")

        # 현재 연결된 클러스터의 데이터베이스 목록 출력
        db_names = await client.list_database_names()
        print(f"현재 데이터베이스 목록: {db_names}")

    except Exception as e:
        print(f"❌ 연결 실패: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_connection())
