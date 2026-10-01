"""
Supabase 클라이언트 연동 모듈
- Supabase 공식 Python SDK(supabase-py)를 사용하여 클라이언트를 생성합니다.
- 환경 변수는 보안 및 규칙 준수를 위해 반드시 os.getenv()를 통해 참조합니다.
- 데이터베이스 조회 시 Raw SQL을 사용하지 않고 supabase-py 쿼리 빌더 인터페이스를 사용합니다.
"""

import os
from typing import Optional
from supabase import create_client, Client


def get_supabase_client() -> Optional[Client]:
    """
    Supabase 클라이언트 인스턴스를 반환합니다.
    환경 변수가 누락되었거나 연결에 실패한 경우 사용자 친화적인 한국어 안내 메시지를 출력합니다.
    """
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_key: Optional[str] = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        print("[안내] SUPABASE_URL 또는 SUPABASE_KEY 환경 변수가 설정되지 않았습니다. (더미 데이터를 사용합니다)")
        return None

    try:
        # supabase-py의 create_client 함수를 사용하여 클라이언트 생성
        client: Client = create_client(supabase_url, supabase_key)
        return client
    except Exception as e:
        print(f"[오류] Supabase 클라이언트 초기화 중 오류가 발생했습니다: {e}")
        return None


def get_supabase_admin_client() -> Optional[Client]:
    """
    Supabase Admin(서비스 롤) 클라이언트 인스턴스를 반환합니다.
    사용자 비밀번호 강제 변경 등 관리자 권한 API 호출 시 사용됩니다.
    SUPABASE_SERVICE_ROLE_KEY 또는 SUPABASE_SERVICE_KEY 환경 변수를 참조합니다.
    """
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    service_key: Optional[str] = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY")
    )

    if not supabase_url or not service_key:
        return None

    try:
        client: Client = create_client(supabase_url, service_key)
        return client
    except Exception as e:
        print(f"[오류] Supabase Admin 클라이언트 초기화 오류: {e}")
        return None
