"""
메인 라우트 모듈
쇼핑몰 메인 페이지 및 상품 목록 조회를 담당합니다.
"""

from flask import Blueprint, render_template
from app.supabase_client import get_supabase_client

# 메인 기능을 담당할 블루프린트 객체 생성
main_bp = Blueprint("main", __name__)

# 더미 상품 데이터 (몬치치 콜라보레이션 상품 4개)
# 초보자도 쉽게 이해할 수 있도록 파이썬 리스트/딕셔너리 형태로 정의합니다.
PRODUCTS = [
    {
        "id": 1,
        "name": "[몬치치 컬렉션] 베이비 블루 턱받이 인형 (20cm)",
        "category": "PLUSH DOLL",
        "price": "38,000",
        "original_price": "45,000",
        "badge": "BEST",
        "badge_color": "danger",
        "image": "https://images.unsplash.com/photo-1559715745-e1b12395b210?auto=format&fit=crop&w=600&q=80",
        "description": "사랑스러운 스카이블루 레이스 턱받이를 한 시그니처 몬치치 오리지널 인형입니다.",
    },
    {
        "id": 2,
        "name": "[VIBE x 몬치치] 자수 오버핏 후드 티셔츠",
        "category": "APPAREL",
        "price": "69,000",
        "original_price": "89,000",
        "badge": "LIMITED",
        "badge_color": "primary",
        "image": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&q=80",
        "description": "가슴에 섬세한 몬치치 포인트 자수가 새겨진 소프트 코튼 오버핏 스웻 후디입니다.",
    },
    {
        "id": 3,
        "name": "[몬치치 컬렉션] 플러피 에코백 & 키링 세트",
        "category": "ACC",
        "price": "29,000",
        "original_price": "35,000",
        "badge": "HOT",
        "badge_color": "warning",
        "image": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=600&q=80",
        "description": "포근한 촉감의 몬치치 얼굴 키링과 데일리로 가볍게 메기 좋은 캔버스 토트백 세트입니다.",
    },
    {
        "id": 4,
        "name": "[몬치치 파자마] 파스텔 체크 수면 잠옷 세트",
        "category": "LOUNGE",
        "price": "52,000",
        "original_price": "68,000",
        "badge": "NEW",
        "badge_color": "success",
        "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=600&q=80",
        "description": "하늘색 깅엄체크 패턴과 귀여운 몬치치 그래픽이 담긴 부드러운 순면 홈웨어입니다.",
    },
]


@main_bp.route("/")
def index():
    """
    쇼핑몰 메인 페이지 뷰 함수
    - Supabase 클라이언트가 활성화되어 있으면 supabase-py API를 통해 상품 데이터를 조회합니다.
    - 미설정 시 기본 몬치치 컬렉션 더미 데이터를 표시합니다.
    - 코딩 규칙 준수: raw SQL 금지, supabase-py SDK만 사용, 한국어 예외 처리.
    """
    display_products = PRODUCTS

    supabase = get_supabase_client()
    if supabase:
        try:
            # supabase-py 쿼리 빌더 인터페이스 사용 (raw SQL 사용 금지)
            response = supabase.table("products").select("*").limit(4).execute()
            if response.data and len(response.data) > 0:
                display_products = response.data
        except Exception as e:
            # 오류 발생 시 한국어 안내 로그 출력 후 기본 데이터 유지
            print(f"[안내] Supabase 'products' 테이블 조회 실패 (기본 상품 표시): {e}")

    return render_template("index.html", products=display_products)
