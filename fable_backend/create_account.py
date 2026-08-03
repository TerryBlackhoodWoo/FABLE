"""
계정 발급 스크립트 (CLI). 최초 개발자 계정, 또는 배포처별 계정을 발급할 때 사용.

사용법:
  python create_account.py --type developer --label "본인 테스트용"
  python create_account.py --type deployment --label "블로그X 제휴" --limit 100

주의: 발급된 원문 API 키는 이 실행 시점에만 출력된다. DB에는 해시만 저장되므로
      반드시 이 출력값을 안전한 곳(비밀번호 관리자 등)에 즉시 저장할 것.
"""

import argparse
import asyncio
import secrets

import database_pg
from dao import account_dao
from services.auth_service import hash_api_key


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["developer", "deployment"], required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--limit", type=int, default=None, help="deployment 계정의 일일 요청 한도"
    )
    args = parser.parse_args()

    if args.type == "deployment" and args.limit is None:
        parser.error(
            "--type deployment 인 경우 --limit(일일 한도)을 반드시 지정하세요."
        )

    prefix = "fbl_dev" if args.type == "developer" else "fbl_dep"
    raw_key = f"{prefix}_{secrets.token_urlsafe(24)}"
    key_hash = hash_api_key(raw_key)

    await database_pg.connect()
    try:
        account = await account_dao.create_account(
            key_hash=key_hash,
            key_prefix=raw_key[: len(prefix) + 9],  # 접두어 + 짧은 식별 조각만 저장
            account_type=args.type,
            label=args.label,
            daily_limit=args.limit,
        )
    finally:
        await database_pg.close()

    print("계정 생성 완료.")
    print(f"  id: {account['id']}")
    print(f"  type: {account['account_type']}")
    print(f"  daily_limit: {account['daily_limit']}")
    print()
    print("아래 API 키는 지금만 출력됩니다. 안전한 곳에 즉시 저장하세요:")
    print(f"  {raw_key}")


if __name__ == "__main__":
    asyncio.run(main())
