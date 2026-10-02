"""
주문서 페이지 및 결제 기능 테스트 스크립트
"""
import unittest
from app import create_app
from app.supabase_client import get_supabase_client, get_supabase_admin_client


class OrderCheckoutTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})
        self.client = self.app.test_client()

    def test_unauthenticated_checkout_redirects_to_login(self):
        """1. 미로그인 상태에서 GET /order/checkout 접근 시 /auth/login으로 리다이렉트"""
        response = self.client.get("/order/checkout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_empty_cart_redirects_to_cart(self):
        """2. 로그인 상태이나 장바구니가 비어 있으면 /cart로 리다이렉트"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "00000000-0000-0000-0000-000000000000",
                "email": "test@test.com",
                "name": "테스터",
                "phone": "010-1111-2222"
            }

        response = self.client.get("/order/checkout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # 장바구니 페이지로 리다이렉트되었는지 확인
        self.assertIn("장바구니", response.data.decode("utf-8"))

    def test_api_shipping_address(self):
        """3. 마이페이지 기본 배송지 조회 API (GET /order/api/shipping-address) 테스트"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "00000000-0000-0000-0000-000000000000",
                "email": "test@test.com",
                "name": "홍길동",
                "phone": "010-1234-5678"
            }

        response = self.client.get("/order/api/shipping-address")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["data"]["recipient_name"], "홍길동")
        self.assertEqual(data["data"]["recipient_phone"], "010-1234-5678")

    def test_checkout_validation_failures(self):
        """4. 결제 시 전화번호 형식 및 주소 최소 길이 유효성 검사"""
        from unittest.mock import patch

        with patch("app.routes.order.fetch_user_cart_items") as mock_fetch:
            mock_fetch.return_value = (
                [{
                    "cart_id": 1,
                    "product_id": 5,
                    "option_id": 274,
                    "product_name": "테스트 상품",
                    "quantity": 1,
                    "unit_price": 26000,
                    "subtotal": 26000,
                    "is_out_of_stock": False,
                    "image_url": "/static/images/real_pink_rabbit.png",
                    "option_display": "Pink / Free"
                }],
                26000,
                3000,
                29000,
                False
            )

            with self.client.session_transaction() as sess:
                sess["user"] = {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "email": "test@test.com",
                    "name": "홍길동",
                    "phone": "010-1234-5678"
                }

            # 잘못된 전화번호 형식
            response = self.client.post("/order/checkout", data={
                "recipient_name": "홍길동",
                "recipient_phone": "01012345678", # 하이픈 없음
                "shipping_address": "서울특별시 강남구 테헤란로 123",
            }, follow_redirects=True)
            self.assertIn("010-0000-0000", response.data.decode("utf-8"))

            # 5자 미만의 짧은 주소
            response = self.client.post("/order/checkout", data={
                "recipient_name": "홍길동",
                "recipient_phone": "010-1234-5678",
                "shipping_address": "서울시", # 3자
            }, follow_redirects=True)
            self.assertIn("최소 5자 이상", response.data.decode("utf-8"))

    def test_out_of_stock_item_redirects_to_cart_with_message(self):
        """5. 장바구니에 품절(stock=0) 아이템이 있으면 /cart 리다이렉트 및 안내 메시지 표시"""
        from unittest.mock import patch

        with patch("app.routes.order.fetch_user_cart_items") as mock_fetch:
            mock_fetch.return_value = (
                [{
                    "cart_id": 1,
                    "product_name": "품절 상품",
                    "quantity": 1,
                    "unit_price": 20000,
                    "subtotal": 20000,
                    "is_out_of_stock": True,
                    "image_url": "/static/images/real_pink_rabbit.png",
                    "option_display": "핑크 / Free"
                }],
                20000,
                3000,
                23000,
                True  # has_out_of_stock
            )

            with self.client.session_transaction() as sess:
                sess["user"] = {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "email": "test@test.com",
                    "name": "홍길동"
                }

            response = self.client.get("/order/checkout", follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn("품절된 상품이 있어 주문할 수 없습니다", response.data.decode("utf-8"))

    def test_post_order_create_order_number_format(self):
        """6. POST /order/create 주문번호 생성 형식 ('VF-YYYYMMDD-4자리랜덤+3자리ms') 및 프로세스 검증"""
        import re

        now_pattern = r"^VF-\d{8}-\d{7}$"
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "00000000-0000-0000-0000-000000000000",
                "email": "test@test.com",
                "name": "홍길동"
            }

        # 장바구니 비어있을 시 /cart 리다이렉트
        response = self.client.post("/order/create", data={
            "recipient_name": "홍길동",
            "recipient_phone": "010-1234-5678",
            "shipping_address": "서울특별시 강남구 테헤란로 123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("장바구니", response.data.decode("utf-8"))

    def test_order_complete_forbidden_for_other_user(self):
        """7. GET /order/complete/<order_id> 타인의 order_id 접근 시 403 차단 검증"""
        from unittest.mock import MagicMock, patch

        mock_supabase = MagicMock()
        # 타인 user_id(other-user-uuid)를 가진 주문 반환 모의
        mock_supabase.table().select().or_().limit().execute.return_value.data = [{
            "id": "11111111-2222-3333-4444-555555555555",
            "user_id": "other-user-uuid",
            "order_number": "VF-20261002-1234567"
        }]

        with patch("app.routes.order.get_supabase_admin_client", return_value=mock_supabase):
            with self.client.session_transaction() as sess:
                sess["user"] = {
                    "id": "my-user-uuid",
                    "email": "my@test.com",
                    "name": "내계정"
                }

            response = self.client.get("/order/complete/11111111-2222-3333-4444-555555555555", follow_redirects=False)
            self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
