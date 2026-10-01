#!/usr/bin/env python3
"""
회원가입 디버깅 - 상세 에러 로그 확인
"""
import requests

BASE_URL = "http://127.0.0.1:5000"

response = requests.post(
    f"{BASE_URL}/auth/signup",
    json={
        "email": "test_debug@example.com",
        "full_name": "디버그 테스트",
        "password": "TestPass123!",
        "password_confirm": "TestPass123!"
    }
)
print(f"상태 코드: {response.status_code}")
print(f"응답 본문:")
print(response.text[:1000])
