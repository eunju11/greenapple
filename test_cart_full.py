#!/usr/bin/env python3
"""
장바구니 추가 전체 테스트 (회원가입 + 로그인 + 장바구니 추가)
"""
import requests

BASE_URL = "http://127.0.0.1:5000"

# 세션 생성
session = requests.Session()

print("=== 1. 회원가입 ===")
response = session.post(
    f"{BASE_URL}/auth/signup",
    json={
        "email": "test_user@example.com",
        "full_name": "테스트 사용자",
        "password": "TestPass123!",
        "password_confirm": "TestPass123!"
    }
)
print(f"상태 코드: {response.status_code}")
print(f"응답: {response.json()}")
print(f"쿠키: {session.cookies}")

if response.status_code not in [200, 201]:
    print("회원가입 실패!")
    exit(1)

print("\n=== 2. 세션 쿠키 확인 후 장바구니 추가 ===")
response = session.post(
    f"{BASE_URL}/cart/add",
    json={"product_option_id": 10, "quantity": 1}
)
print(f"상태 코드: {response.status_code}")
print(f"응답: {response.json()}")

print("\n=== 3. 다시 로그인 (새 세션) ===")
session2 = requests.Session()
response = session2.post(
    f"{BASE_URL}/auth/signin",
    json={
        "email": "test_user@example.com",
        "password": "TestPass123!"
    }
)
print(f"상태 코드: {response.status_code}")
print(f"응답: {response.json()}")
print(f"쿠키: {session2.cookies}")

if response.status_code == 200:
    print("\n=== 4. 로그인 후 장바구니 추가 ===")
    response = session2.post(
        f"{BASE_URL}/cart/add",
        json={"product_option_id": 10, "quantity": 1}
    )
    print(f"상태 코드: {response.status_code}")
    print(f"응답: {response.json()}")
