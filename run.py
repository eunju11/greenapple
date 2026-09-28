"""
VIBE-FASHION 애플리케이션 진입점 (Entry Point)
앱 팩토리 함수 create_app()을 호출하여 인스턴스를 생성하고 서버를 구동합니다.
"""

from app import create_app

# 애플리케이션 인스턴스 생성
app = create_app()

if __name__ == "__main__":
    # 개발 서버 실행 (디버그 모드 활성화, 포트 5000)
    print(">>> VIBE-FASHION 웹 서버 시작: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
