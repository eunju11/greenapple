"""
카카오톡 소셜 로그인 및 회원가입 라우트 모듈
- Kakao OAuth 2.0 프로토콜을 사용한 회원가입 및 로그인 처리
- 환경 변수(os.getenv)를 통한 카카오 API 키 참조
- Supabase 클라이언트 연동 및 세션 관리
- 개발 환경 편의를 위한 가이드 및 테스트 로그인 기능 지원
"""

import os
import secrets
import re
from urllib.parse import urlencode
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
import httpx
from app.supabase_client import get_supabase_client

# 인증 기능을 담당할 블루프린트 생성
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# 카카오 OAuth 엔드포인트 상수 정의
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


def get_redirect_uri():
    """
    카카오 Redirect URI 반환
    환경 변수에 지정된 값이 있으면 우선 사용하고, 없으면 요청 호스트 기준 동적 생성합니다.
    """
    env_uri = os.getenv("KAKAO_REDIRECT_URI")
    if env_uri:
        return env_uri
    # Flask url_for를 통해 현재 서버의 절대 URL 생성
    return url_for("auth.kakao_callback", _external=True)


@auth_bp.route("/login")
def login_page():
    """
    회원가입 및 로그인 페이지 화면을 렌더링합니다.
    """
    # 이미 로그인된 상태라면 메인 페이지로 이동
    if "user" in session:
        flash(f"이미 '{session['user'].get('name', '고객')}'님으로 로그인되어 있습니다.", "info")
        return redirect(url_for("main.index"))

    client_id = os.getenv("KAKAO_CLIENT_ID")
    is_kakao_configured = bool(client_id and client_id.strip())

    return render_template(
        "auth/login.html",
        is_kakao_configured=is_kakao_configured
    )


@auth_bp.route("/kakao")
def kakao_login():
    """
    카카오 인증 요청 시작
    카카오 인가 코드 발급 페이지(https://kauth.kakao.com/oauth/authorize)로 사용자를 리다이렉트합니다.
    """
    client_id = os.getenv("KAKAO_CLIENT_ID")
    if not client_id or not client_id.strip():
        # 카카오 클라이언트 ID가 설정되지 않은 경우 안내 페이지로 이동
        return render_template("auth/guide.html", redirect_uri=get_redirect_uri())

    # CSRF 공격 방지를 위한 무작위 state 토큰 생성 및 세션 저장
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    redirect_uri = get_redirect_uri()

    # 카카오 인증 페이지 파라미터 구성 (scope는 콘솔 동의항목 설정을 따르도록 유연하게 설정)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    }

    kakao_auth_redirect = f"{KAKAO_AUTH_URL}?{urlencode(params)}"
    return redirect(kakao_auth_redirect)


@auth_bp.route("/kakao/callback")
def kakao_callback():
    """
    카카오 인증 완료 후 인가 코드를 수신하는 콜백 라우트
    1. 인가 코드로 카카오 액세스 토큰(Access Token) 발급 요청
    2. 액세스 토큰으로 카카오 사용자 정보(닉네임, 프로필 사진, 이메일) 조회
    3. Supabase 회원 데이터 동기화 및 Flask 세션 등록
    """
    # 1. 사용자가 동의를 취소했거나 카카오 오류가 발생한 경우 처리
    error = request.args.get("error")
    error_description = request.args.get("error_description", "")
    if error:
        flash(f"카카오 로그인이 취소되었거나 실패했습니다. ({error_description or error})", "warning")
        return redirect(url_for("auth.login_page"))

    code = request.args.get("code")
    if not code:
        flash("카카오 인증 코드를 전달받지 못했습니다. 다시 시도해주세요.", "danger")
        return redirect(url_for("auth.login_page"))

    # 2. CSRF state 검증 (세션에 저장된 값과 비교)
    state = request.args.get("state")
    saved_state = session.pop("oauth_state", None)
    if saved_state and state != saved_state:
        flash("비정상적인 요청(CSRF)이 감지되었습니다. 다시 시도해주세요.", "danger")
        return redirect(url_for("auth.login_page"))

    client_id = os.getenv("KAKAO_CLIENT_ID")
    client_secret = os.getenv("KAKAO_CLIENT_SECRET")
    redirect_uri = get_redirect_uri()

    # 3. 인가 코드를 사용하여 토큰 요청
    token_data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    if client_secret:
        token_data["client_secret"] = client_secret

    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            # 3-1. 카카오 토큰 발급 API 호출
            token_res = client.post(KAKAO_TOKEN_URL, data=token_data, headers=headers)
            if token_res.status_code != 200:
                print(f"[카카오 토큰 발급 실패]: {token_res.text}")
                flash("카카오 토큰 발급에 실패했습니다. 카카오 앱 설정을 확인해주세요.", "danger")
                return redirect(url_for("auth.login_page"))

            token_json = token_res.json()
            access_token = token_json.get("access_token")

            # 3-2. 카카오 사용자 정보 조회 API 호출
            user_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
            }
            user_res = client.get(KAKAO_USER_INFO_URL, headers=user_headers)
            if user_res.status_code != 200:
                print(f"[카카오 사용자 정보 조회 실패]: {user_res.text}")
                flash("카카오 사용자 정보를 가져오지 못했습니다.", "danger")
                return redirect(url_for("auth.login_page"))

            user_data = user_res.json()

    except Exception as e:
        print(f"[카카오 연동 네트워크 오류]: {e}")
        flash("카카오 서버와 통신하는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.", "danger")
        return redirect(url_for("auth.login_page"))

    # 4. 카카오 사용자 프로필 정보 추출
    kakao_id = user_data.get("id")
    kakao_account = user_data.get("kakao_account", {})
    kakao_profile = kakao_account.get("profile", {})

    nickname = kakao_profile.get("nickname") or user_data.get("properties", {}).get("nickname") or "카카오 회원"
    profile_image = (
        kakao_profile.get("profile_image_url") or 
        user_data.get("properties", {}).get("profile_image") or 
        url_for("static", filename="images/strawberry_icon.svg")
    )
    email = kakao_account.get("email") or f"kakao_{kakao_id}@vibe-fashion.com"

    # 5. Flask 세션에 사용자 정보 저장 (신규 가입 및 로그인 완료)
    session_user = {
        "id": f"kakao_{kakao_id}",
        "provider": "kakao",
        "provider_id": str(kakao_id),
        "name": nickname,
        "email": email,
        "avatar_url": profile_image,
        "grade": "BRONZE",
    }
    session["user"] = session_user
    session.modified = True

    # 6. Supabase 데이터베이스에 회원 정보 동기화 (연결된 경우)
    supabase = get_supabase_client()
    if supabase:
        try:
            # profiles 테이블에 회원 정보 저장 시도
            profile_payload = {
                "email": email,
                "full_name": nickname,
                "avatar_url": profile_image,
                "role": "customer",
                "grade": "BRONZE",
            }
            # supabase-py 쿼리 빌더를 사용하여 저장
            supabase.table("profiles").upsert(profile_payload, on_conflict="email").execute()
            print(f"[안내] Supabase 회원 프로필 동기화 완료: {email}")
        except Exception as e:
            # auth.users 외래 키 제약 조건 등으로 인한 에러 시에도 로그만 기록하고 로그인은 유지
            print(f"[안내] Supabase 프로필 동기화 시도 (계속 진행): {e}")

    flash(f"🍓 '{nickname}'님 환영합니다! 카카오 계정으로 간편 가입 및 로그인이 완료되었습니다.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/mock")
def mock_login():
    """
    개발 환경용 카카오 간편 로그인/회원가입 시뮬레이터
    - API 키가 아직 없더라도 즉시 UI와 가입 기능을 테스트해볼 수 있도록 지원합니다.
    """
    mock_user = {
        "id": "kakao_demo_777",
        "provider": "kakao",
        "provider_id": "777888",
        "name": "치무탄 딸기요정",
        "email": "chimutan_berry@kakao.com",
        "avatar_url": url_for("static", filename="images/strawberry_icon.svg"),
        "grade": "VIP",
    }
    session["user"] = mock_user
    session.modified = True

    flash("🍓 [개발 테스트 모드] 카카오 계정으로 간편 가입 및 로그인이 완료되었습니다!", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/signup", methods=["POST"])
def email_signup():
    """
    이메일/비밀번호 기반 회원가입 처리 핸들러
    JSON 또는 Form 데이터 모두 지원
    - 이메일 유효성, 비밀번호 복잡도(8자 이상, 영문+숫자+특수문자) 및 확인 일치 검증
    - Supabase auth.sign_up() 호출 및 profiles 테이블 동기화
    """
    # JSON 또는 Form 데이터 파싱
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip()
    name = data.get("full_name", data.get("name", "")).strip()
    password = data.get("password", "").strip()
    confirm_password = data.get("password_confirm", data.get("confirm_password", "")).strip()

    if not email or not name or not password or not confirm_password:
        error_msg = "모든 필수 입력 항목을 작성해주세요."
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("auth.login_page") + "#email-signup")

    # 이메일 형식 정규식 검증
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        error_msg = "올바른 이메일 형식을 입력해주세요."
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("auth.login_page") + "#email-signup")

    # 비밀번호 확인 일치 검증
    if password != confirm_password:
        error_msg = "비밀번호와 확인용 비밀번호가 일치하지 않습니다."
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("auth.login_page") + "#email-signup")

    # 비밀번호 정책 검증 (최소 8자, 영문 + 숫자 + 특수문자 조합)
    if len(password) < 8:
        error_msg = "비밀번호는 최소 8자 이상이어야 합니다."
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("auth.login_page") + "#email-signup")

    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))
    if not (has_letter and has_digit and has_special):
        error_msg = "비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다."
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("auth.login_page") + "#email-signup")

    supabase = get_supabase_client()
    user_id = f"user_{secrets.token_hex(8)}"
    avatar_url = "/static/images/strawberry_icon.svg"

    if supabase:
        try:
            sign_up_res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": name
                    }
                }
            })
            if sign_up_res and sign_up_res.user:
                user_id = sign_up_res.user.id

            # profiles 테이블에 회원 정보 저장 시도 (provider 컬럼 미존재 시 기본 정보만 저장)
            profile_payload = {
                "id": user_id,
                "email": email,
                "full_name": name,
                "avatar_url": avatar_url,
                "role": "customer",
                "grade": "BRONZE",
            }
            try:
                supabase.table("profiles").upsert({**profile_payload, "provider": "email"}).execute()
            except Exception as pe1:
                print(f"[안내] provider 포함 upsert 실패: {pe1}")
                try:
                    supabase.table("profiles").upsert(profile_payload).execute()
                except Exception as pe2:
                    print(f"[안내] Supabase profiles 저장 실패: {pe2}")
        except Exception as e:
            err_msg = str(e).lower()
            if "already registered" in err_msg or "already exists" in err_msg:
                error_msg = "이미 가입된 이메일 주소입니다. 로그인해주세요."
                if request.is_json:
                    return jsonify({"success": False, "message": error_msg}), 409
                flash(error_msg, "warning")
                return redirect(url_for("auth.login_page") + "#email-login")
            print(f"[오류] Supabase 이메일 회원가입: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "회원가입 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            if request.is_json:
                return jsonify({"success": False, "message": error_msg}), 500
            flash(error_msg, "danger")
            return redirect(url_for("auth.login_page") + "#email-signup")

    # 세션에 로그인 상태 등록
    session["user"] = {
        "id": user_id,
        "provider": "email",
        "provider_id": email,
        "name": name,
        "email": email,
        "avatar_url": avatar_url,
        "grade": "BRONZE",
    }
    session.modified = True

    success_msg = f"🍓 '{name}'님 환영합니다! 이메일 회원가입 및 로그인이 완료되었습니다."
    if request.is_json:
        return jsonify({"success": True, "message": success_msg, "user": session["user"]}), 201
    
    flash(success_msg, "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/signin", methods=["POST"])
def email_signin():
    """
    이메일/비밀번호 기반 로그인 처리 핸들러
    JSON 또는 Form 데이터 모두 지원
    """
    # JSON 또는 Form 데이터 파싱
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        error_msg = "이메일과 비밀번호를 모두 입력해주세요."
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("auth.login_page") + "#email-login")

    supabase = get_supabase_client()
    user_name = email.split("@")[0]
    user_id = f"user_{secrets.token_hex(8)}"
    avatar_url = "/static/images/strawberry_icon.svg"
    grade = "BRONZE"

    if supabase:
        try:
            sign_in_res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if not sign_in_res or not sign_in_res.user:
                error_msg = "이메일 또는 비밀번호가 일치하지 않습니다."
                if request.is_json:
                    return jsonify({"success": False, "message": error_msg}), 401
                flash(error_msg, "danger")
                return redirect(url_for("auth.login_page") + "#email-login")

            user_id = sign_in_res.user.id
            if sign_in_res.user.user_metadata and sign_in_res.user.user_metadata.get("full_name"):
                user_name = sign_in_res.user.user_metadata.get("full_name")

            # profiles 테이블 조회
            try:
                prof_res = supabase.table("profiles").select("*").eq("email", email).limit(1).execute()
                if prof_res.data and len(prof_res.data) > 0:
                    p = prof_res.data[0]
                    user_name = p.get("full_name") or user_name
                    avatar_url = p.get("avatar_url") or avatar_url
                    grade = p.get("grade") or grade
            except Exception as pe:
                print(f"[안내] profiles 조회: {pe}")
        except Exception as e:
            err_msg = str(e).lower()
            print(f"[안내] Supabase 로그인 인증: {e}")
            error_msg = "이메일 또는 비밀번호가 올바르지 않습니다."
            if request.is_json:
                return jsonify({"success": False, "message": error_msg}), 401
            flash(error_msg, "danger")
            return redirect(url_for("auth.login_page") + "#email-login")

    # 세션 로그인 처리
    session["user"] = {
        "id": str(user_id),
        "provider": "email",
        "provider_id": email,
        "name": user_name,
        "email": email,
        "avatar_url": avatar_url,
        "grade": grade,
    }
    session.modified = True

    success_msg = f"🍓 '{user_name}'님 반갑습니다! 로그인이 완료되었습니다."
    if request.is_json:
        return jsonify({"success": True, "message": success_msg, "user": session["user"]}), 200
    
    flash(success_msg, "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/logout")
def logout():
    """
    로그아웃 처리
    - 세션에서 사용자 정보를 제거합니다.
    """
    user_name = session.get("user", {}).get("name", "회원")
    session.pop("user", None)
    session.modified = True

    flash(f"'{user_name}'님 안전하게 로그아웃되었습니다. 다음에 또 만나요! 🍓", "info")
    return redirect(url_for("main.index"))
