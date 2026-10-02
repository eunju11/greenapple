"""
VIBE-FASHION 애플리케이션 팩토리 모듈
Flask의 앱 팩토리 패턴(Application Factory Pattern)을 구현합니다.
"""

from flask import Flask
import os
from dotenv import load_dotenv

# .env 파일의 환경 변수를 로드합니다.
load_dotenv()


def create_app(test_config=None):
    """
    Flask 애플리케이션을 생성하고 설정하는 팩토리 함수입니다.
    초보자도 이해하기 쉬운 구조로 라우트와 설정을 한 곳에서 관리합니다.
    """
    # Flask 앱 인스턴스 생성 (static과 template 폴더 지정)
    app = Flask(__name__, instance_relative_config=True)

    # 기본 설정 등록
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "vibe-fashion-default-secret-key"),
        SUPABASE_URL=os.getenv("SUPABASE_URL", ""),
        SUPABASE_KEY=os.getenv("SUPABASE_KEY", ""),
    )

    if test_config is not None:
        # 테스트 환경 설정이 전달된 경우 덮어씌웁니다.
        app.config.from_mapping(test_config)

    # 블루프린트(Blueprint) 등록 - 기능별로 분리된 라우트 모듈을 앱에 연결합니다.
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.order import order_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(admin_bp)

    # 한국어 및 Bootstrap 5 스타일의 에러 핸들러 등록
    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(error):
        """존재하지 않는 페이지 요청 시 404 에러 화면을 한국어로 렌더링합니다."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        """서버 내부 오류 발생 시 500 에러 화면을 한국어로 렌더링합니다."""
        return render_template("errors/500.html"), 500

    return app
