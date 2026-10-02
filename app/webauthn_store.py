"""
생체인증(WebAuthn / Passkey) 자격증명 저장 및 관리 모듈
- SQLite DB(instance/webauthn.sqlite3)에 브라우저 생체인증(지문/Face ID/Windows Hello) 키 저장
- Supabase auth.admin user_metadata와 상호 동기화 지원
"""

import os
import sqlite3
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.supabase_client import get_supabase_admin_client


def get_db_path() -> str:
    """SQLite 데이터베이스 파일 경로 반환"""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    instance_dir = os.path.join(base_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True)
    return os.path.join(instance_dir, "webauthn.sqlite3")


def init_db():
    """WebAuthn 자격증명 테이블 초기화"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS webauthn_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credential_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                email TEXT NOT NULL,
                public_key TEXT NOT NULL,
                sign_count INTEGER DEFAULT 0,
                device_name TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_webauthn_user_id ON webauthn_credentials(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_webauthn_email ON webauthn_credentials(email)")
        conn.commit()


# 앱 로딩 시 테이블 초기화
init_db()


def save_credential(
    credential_id: str,
    user_id: str,
    email: str,
    public_key: str,
    sign_count: int = 0,
    device_name: str = "생체인증 디바이스"
) -> bool:
    """
    생체인증 등록 자격증명을 로컬 DB에 저장하고 Supabase user_metadata에 백업합니다.
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db_path = get_db_path()

    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO webauthn_credentials 
                (credential_id, user_id, email, public_key, sign_count, device_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (credential_id, user_id, email, public_key, sign_count, device_name, now_str))
            conn.commit()
    except Exception as e:
        print(f"[오류] WebAuthn 로컬 DB 저장 실패: {e}")
        return False

    # Supabase user_metadata 동기화 (클라우드 백업)
    try:
        admin_supabase = get_supabase_admin_client()
        if admin_supabase and hasattr(admin_supabase, "auth") and hasattr(admin_supabase.auth, "admin"):
            u_info = admin_supabase.auth.admin.get_user_by_id(user_id)
            if u_info and u_info.user:
                meta = dict(u_info.user.user_metadata or {})
                creds = meta.get("webauthn_credentials", [])
                # 중복 제거 후 추가
                creds = [c for c in creds if c.get("credential_id") != credential_id]
                creds.append({
                    "credential_id": credential_id,
                    "device_name": device_name,
                    "created_at": now_str,
                })
                meta["webauthn_credentials"] = creds
                admin_supabase.auth.admin.update_user_by_id(user_id, {"user_metadata": meta})
    except Exception as se:
        print(f"[안내] Supabase WebAuthn 메타데이터 동기화: {se}")

    return True


def get_credential(credential_id: str) -> Optional[Dict[str, Any]]:
    """credential_id로 단일 자격증명 조회"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM webauthn_credentials WHERE credential_id = ? LIMIT 1", (credential_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
    return None


def get_user_credentials(user_id: str) -> List[Dict[str, Any]]:
    """특정 사용자의 등록된 모든 생체인증 자격증명 목록 조회"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM webauthn_credentials WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_credentials_by_email(email: str) -> List[Dict[str, Any]]:
    """이메일 주소로 등록된 생체인증 자격증명 조회"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM webauthn_credentials WHERE email = ? ORDER BY id DESC", (email,))
        return [dict(r) for r in cur.fetchall()]


def update_sign_count(credential_id: str, new_count: int):
    """인증 서명 카운트 갱신 (리플레이 공격 방지)"""
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE webauthn_credentials SET sign_count = ? WHERE credential_id = ?", (new_count, credential_id))
            conn.commit()
    except Exception as e:
        print(f"[오류] WebAuthn 카운트 갱신 실패: {e}")


def delete_credential(credential_id: str, user_id: str) -> bool:
    """생체인증 기기 등록 해제"""
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM webauthn_credentials WHERE credential_id = ? AND user_id = ?", (credential_id, user_id))
            conn.commit()
    except Exception as e:
        print(f"[오류] WebAuthn 삭제 실패: {e}")
        return False

    # Supabase 메타데이터 동기화
    try:
        admin_supabase = get_supabase_admin_client()
        if admin_supabase and hasattr(admin_supabase, "auth") and hasattr(admin_supabase.auth, "admin"):
            u_info = admin_supabase.auth.admin.get_user_by_id(user_id)
            if u_info and u_info.user:
                meta = dict(u_info.user.user_metadata or {})
                creds = meta.get("webauthn_credentials", [])
                creds = [c for c in creds if c.get("credential_id") != credential_id]
                meta["webauthn_credentials"] = creds
                admin_supabase.auth.admin.update_user_by_id(user_id, {"user_metadata": meta})
    except Exception as se:
        print(f"[안내] Supabase WebAuthn 메타데이터 동기화: {se}")

    return True
