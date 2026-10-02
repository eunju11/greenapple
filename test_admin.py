"""
관리자 대시보드 및 기능 단위 테스트 스크립트
"""

import unittest
from app import create_app
from app.supabase_client import get_supabase_admin_client


class AdminTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-admin-secret-key"})
        self.client = self.app.test_client()
        self.admin = get_supabase_admin_client()

    def test_unauthenticated_access_denied(self):
        """1. 미로그인 사용자의 관리자 페이지 접근 시 로그인 페이지로 리다이렉트"""
        res = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/auth/login", res.headers.get("Location", ""))

    def test_admin_dashboard_rendering(self):
        """2. 관리자 계정 로그인 시 대시보드 및 인기 상품, 회원, 주문 데이터 렌더링 검증"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "001aa710-9d3d-46e0-b24d-4c22c34fdd5f",
                "name": "관리자",
                "email": "strawberry_new@vibe-fashion.com",
                "role": "admin"
            }

        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("관리자 대시보드", html)
        self.assertIn("구매자 수요 인기제품", html)
        self.assertIn("회원 정보 관리", html)

    def test_api_order_detail(self):
        """3. 주문 상세 API (GET /admin/api/orders/<order_id>) 정상 동작 검증"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "001aa710-9d3d-46e0-b24d-4c22c34fdd5f",
                "name": "관리자",
                "email": "strawberry_new@vibe-fashion.com",
                "role": "admin"
            }

        order_res = self.admin.table("orders").select("id").limit(1).execute()
        if order_res.data:
            order_id = order_res.data[0]["id"]
            res = self.client.get(f"/admin/api/orders/{order_id}")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertIn("order_items", data.get("order", {}))

    def test_inventory_page_rendering(self):
        """4. 관리자 재고 관리 페이지 (GET /admin/inventory) 렌더링 검증"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "001aa710-9d3d-46e0-b24d-4c22c34fdd5f",
                "name": "관리자",
                "email": "strawberry_new@vibe-fashion.com",
                "role": "admin"
            }

        res = self.client.get("/admin/inventory")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("재고 관리", html)
        self.assertIn("총 관리 품목(SKU)", html)
        self.assertIn("현재 재고", html)

    def test_inventory_stock_update_and_sync(self):
        """5. 재고 수량 직접 수정 및 상품 총재고 동기화 검증"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "001aa710-9d3d-46e0-b24d-4c22c34fdd5f",
                "name": "관리자",
                "email": "strawberry_new@vibe-fashion.com",
                "role": "admin"
            }

        # 옵션 274 재고 30으로 설정
        res = self.client.post("/admin/inventory/options/274/stock", json={"stock": 30})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["new_stock"], 30)

        # 델타 +10 적용
        res_delta = self.client.post("/admin/inventory/options/274/stock", json={"delta": 10})
        self.assertEqual(res_delta.status_code, 200)
        self.assertEqual(res_delta.get_json()["new_stock"], 40)

        # 원래 재고(15)로 복구
        self.client.post("/admin/inventory/options/274/stock", json={"stock": 15})

    def test_daily_analytics_api(self):
        """6. 일자별 매출 및 주문 통계 API (GET /admin/api/analytics/daily) 검증"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "001aa710-9d3d-46e0-b24d-4c22c34fdd5f",
                "name": "관리자",
                "email": "strawberry_new@vibe-fashion.com",
                "role": "admin"
            }

        for days in [7, 14, 30]:
            res = self.client.get(f"/admin/api/analytics/daily?days={days}")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertEqual(len(data.get("labels", [])), days)
            self.assertEqual(len(data.get("revenues", [])), days)
            self.assertEqual(len(data.get("orders", [])), days)
            self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
