"""
WebAuthn 생체인증 (Passkey / 지문 / Face ID) 기능 테스트
"""

import unittest
from app import create_app
from app.webauthn_store import (
    save_credential,
    get_credential,
    get_user_credentials,
    get_credentials_by_email,
    update_sign_count,
    delete_credential,
)


class WebAuthnTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-webauthn-secret"})
        self.client = self.app.test_client()

    def test_unauthenticated_webauthn_access(self):
        """1. 미로그인 시 등록 옵션 및 목록 조회 차단 (401 반환)"""
        res1 = self.client.post("/auth/webauthn/register-options")
        self.assertEqual(res1.status_code, 401)

        res2 = self.client.get("/auth/webauthn/credentials")
        self.assertEqual(res2.status_code, 401)

    def test_authenticated_register_options(self):
        """2. 로그인 상태에서 생체인증 등록 옵션(challenge, rp, user) 정상 생성"""
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": "11111111-2222-3333-4444-555555555555",
                "name": "생체테스터",
                "email": "bio_tester@example.com",
            }

        res = self.client.post("/auth/webauthn/register-options")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("challenge", data)
        self.assertIn("rp", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["name"], "bio_tester@example.com")

    def test_login_options_generation(self):
        """3. 생체인증 로그인 옵션(challenge, rpId) 정상 생성"""
        # 1-클릭 패스키 로그인 옵션
        res = self.client.post("/auth/webauthn/login-options", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("challenge", data)
        self.assertIn("rpId", data)

    def test_credential_store_crud(self):
        """4. WebAuthn 자격증명 CRUD 저장/조회/삭제 정상 동작"""
        test_cred_id = "test-cred-id-xyz-987"
        test_user_id = "test-user-uuid-999"
        test_email = "test_biometric@example.com"
        test_pub_key = "test-pub-key-data-abc"

        # 1) 저장
        success = save_credential(
            credential_id=test_cred_id,
            user_id=test_user_id,
            email=test_email,
            public_key=test_pub_key,
            sign_count=1,
            device_name="테스트 지문 기기"
        )
        self.assertTrue(success)

        # 2) 조회
        cred = get_credential(test_cred_id)
        self.assertIsNotNone(cred)
        self.assertEqual(cred["email"], test_email)
        self.assertEqual(cred["device_name"], "테스트 지문 기기")

        # 3) 사용자별 조회
        user_creds = get_user_credentials(test_user_id)
        self.assertEqual(len(user_creds), 1)

        # 4) 이메일별 조회
        email_creds = get_credentials_by_email(test_email)
        self.assertEqual(len(email_creds), 1)

        # 5) 서명 카운트 갱신
        update_sign_count(test_cred_id, 2)
        updated_cred = get_credential(test_cred_id)
        self.assertEqual(updated_cred["sign_count"], 2)

        # 6) 삭제
        del_success = delete_credential(test_cred_id, test_user_id)
        self.assertTrue(del_success)
        self.assertIsNone(get_credential(test_cred_id))


if __name__ == "__main__":
    unittest.main()
