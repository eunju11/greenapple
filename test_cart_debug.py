#!/usr/bin/env python3
"""
POST /cart/add 디버깅 테스트
"""
import requests

BASE_URL = "http://127.0.0.1:5000"

# 세션 생성
session = requests.Session()

print("=== 로그인 테스트 ===")
response = session.post(
    f"{BASE_URL}/auth/signin",
    json={
        "email": "test@example.com",
        "password": "TestPass123!"
    }
)
print(f"상태 코드: {response.status_code}")
print(f"응답 본문: {response.text[:500]}")
print(f"쿠키: {session.cookies}")
print(f"헤더: {response.headers}")

print("\n=== 세션 쿠키 확인 후 장바구니 추가 ===")
response = session.post(
    f"{BASE_URL}/cart/add",
    json={"product_option_id": 10, "quantity": 1}
)
print(f"상태 코드: {response.status_code}")
print(f"응답: {response.json()}")
