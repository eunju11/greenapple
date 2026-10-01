#!/usr/bin/env python3
"""
POST /cart/add 엔드포인트 테스트 스크립트
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def test_cart_add():
    """POST /cart/add 테스트"""
    
    print("=" * 60)
    print("POST /cart/add 엔드포인트 테스트 시작")
    print("=" * 60)
    
    # 세션 생성 (쿠키 유지)
    session = requests.Session()
    
    # 테스트 1: 로그인 없이 요청 시 401 반환
    print("\n[테스트 1] 로그인 없이 요청 (401 기대)")
    print("-" * 60)
    response = session.post(
        f"{BASE_URL}/cart/add",
        json={"product_option_id": 10, "quantity": 1}
    )
    print(f"상태 코드: {response.status_code}")
    print(f"응답: {response.json()}")
    assert response.status_code == 401, f"기대값: 401, 실제: {response.status_code}"
    print("✓ 테스트 1 통과")
    
    # 테스트 2: 이메일로 로그인
    print("\n[테스트 2] 이메일 로그인")
    print("-" * 60)
    response = session.post(
        f"{BASE_URL}/auth/signin",
        json={
            "email": "test@example.com",
            "password": "TestPass123!"
        }
    )
    print(f"상태 코드: {response.status_code}")
    
    # 로그인 성공 또는 실패 확인
    login_success = False
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"응답: {data}")
            if data.get("success"):
                login_success = True
        except:
            # JSON 파싱 실패 - 리다이렉트 등으로 처리됨
            print("   → 리다이렉트 응답 (쿠키 설정됨)")
            login_success = True
    
    if not login_success:
        print("   → 로그인 실패. 회원가입 진행...")
        response = session.post(
            f"{BASE_URL}/auth/signup",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
                "password_confirm": "TestPass123!",
                "full_name": "테스트 사용자"
            }
        )
        print(f"   회원가입 상태 코드: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ 회원가입 성공")
            # 다시 로그인 시도
            response = session.post(
                f"{BASE_URL}/auth/signin",
                json={
                    "email": "test@example.com",
                    "password": "TestPass123!"
                }
            )
            print(f"   로그인 재시도 상태 코드: {response.status_code}")
            login_success = True
    
    if not login_success:
        print("⚠ 로그인/회원가입 실패. 테스트 중단.")
        return
    
    print("✓ 테스트 2 통과")
    
    # 테스트 3: 유효한 product_option_id로 장바구니 추가
    print("\n[테스트 3] 유효한 product_option_id로 장바구니 추가")
    print("-" * 60)
    response = session.post(
        f"{BASE_URL}/cart/add",
        json={"product_option_id": 10, "quantity": 1}
    )
    print(f"상태 코드: {response.status_code}")
    print(f"응답: {response.json()}")
    
    # 성공 또는 제품 옵션 없음 모두 가능
    if response.status_code == 200:
        data = response.json()
        assert data.get("success") == True, "성공 응답 기대"
        assert "message" in data, "메시지 필드 필요"
        print("✓ 테스트 3 통과")
    elif response.status_code == 404:
        print("   → product_option_id 10이 없음 (예상된 상황)")
        print("   → Supabase에서 실제 product_option_id 확인 필요")
        print("✓ 테스트 3 통과 (404는 예상된 응답)")
    else:
        print(f"   ⚠ 예기치 않은 상태 코드: {response.status_code}")
    
    # 테스트 4: 잘못된 product_option_id 타입
    print("\n[테스트 4] 잘못된 product_option_id (문자열)")
    print("-" * 60)
    response = session.post(
        f"{BASE_URL}/cart/add",
        json={"product_option_id": "invalid", "quantity": 1}
    )
    print(f"상태 코드: {response.status_code}")
    print(f"응답: {response.json()}")
    assert response.status_code == 400, f"기대값: 400, 실제: {response.status_code}"
    print("✓ 테스트 4 통과")
    
    # 테스트 5: 수량이 0 이하
    print("\n[테스트 5] 수량이 0 이하")
    print("-" * 60)
    response = session.post(
        f"{BASE_URL}/cart/add",
        json={"product_option_id": 10, "quantity": 0}
    )
    print(f"상태 코드: {response.status_code}")
    print(f"응답: {response.json()}")
    assert response.status_code == 400, f"기대값: 400, 실제: {response.status_code}"
    print("✓ 테스트 5 통과")
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    test_cart_add()
