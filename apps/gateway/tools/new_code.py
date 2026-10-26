"""접속 코드 발급: 코드는 사용자에게, 해시는 Render 환경변수 ACCESS_CODE_HASHES(쉼표로 이어 붙임)에.

실행: cd apps/gateway && python tools/new_code.py [--name 홍길동]
"""
import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import hash_code  # noqa: E402


def new_code(n_bytes: int = 16) -> tuple[str, str]:
    code = secrets.token_urlsafe(n_bytes)
    return code, hash_code(code)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="", help="누구에게 줄 코드인지 메모용 (저장하지 않음)")
    args = ap.parse_args()
    code, digest = new_code()
    who = f" ({args.name})" if args.name else ""
    print(f"접속 코드{who}: {code}")
    print(f"해시: {digest}")
    print("→ 코드는 사용자에게 전달(앱 .env의 LLM_API_KEY), 해시는 Render ACCESS_CODE_HASHES에 쉼표로 추가하세요.")
    print("→ 코드는 다시 볼 수 없습니다. 잃어버리면 새로 발급하고 예전 해시를 지우세요.")
