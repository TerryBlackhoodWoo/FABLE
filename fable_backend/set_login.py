"""
기존 계정에 대시보드 로그인용 아이디/비밀번호를 부여하는 CLI.

사용법:
  python set_login.py --account-id <accounts.id> --username terry --password "강력한 비밀번호"

account-id는 create_account.py 실행 시 출력된 "id" 값을 그대로 쓰면 된다.
"""

import argparse
import asyncio

import database_pg
from dao import account_dao
from services.auth_service import hash_password


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    await database_pg.connect()
    try:
        await account_dao.set_login_credentials(
            args.account_id, args.username, hash_password(args.password)
        )
    finally:
        await database_pg.close()

    print(f"로그인 정보 등록 완료: username={args.username}")


if __name__ == "__main__":
    asyncio.run(main())