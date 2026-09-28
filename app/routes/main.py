"""
메인 라우트 모듈
쇼핑몰 메인 페이지 및 상품 목록 조회를 담당합니다.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.supabase_client import get_supabase_client
from datetime import datetime

# 메인 기능을 담당할 블루프린트 객체 생성
main_bp = Blueprint("main", __name__)

# 기본 더미 리뷰 데이터 (구매자 포토/텍스트 리뷰)
INITIAL_REVIEWS = [
    {
        "id": 1,
        "author": "김*늘",
        "rating": 5,
        "product_name": "[치무탄 정품] 핑크 토끼 페이스 인형 파우치 키링",
        "content": "실물 사진이랑 똑같아요! 보송보송 핑크 털에 토끼 귀가 진짜 귀엽고 가방에 걸고 다니니까 포인트 제대로 됩니다 🐰 딸기코도 넘 사랑스러워요!",
        "date": "2026-09-28",
        "verified": True,
        "badge": "BEST 리뷰",
    },
    {
        "id": 2,
        "author": "이*연",
        "rating": 5,
        "product_name": "[스페셜 화보] 몬치치 & 치무탄 3종 룩북 에디션",
        "content": "스트로베리 토끼랑 핑크 치무탄, 가방 베어 키링 3종 실물 깡패예요 ㅠㅠ 친구들이랑 하나씩 나눠가졌는데 다들 너무 좋아해요!",
        "date": "2026-09-27",
        "verified": True,
        "badge": "포토 리뷰",
    },
    {
        "id": 3,
        "author": "박*준",
        "rating": 5,
        "product_name": "[치무탄 스트로베리] 레드 딸기 토끼 페이스 파우치",
        "content": "딸기 디테일이랑 초록색 꼭지 부분이 진짜 귀여워요! 가방에 포인트 주기에 이만한 게 없네요.",
        "date": "2026-09-26",
        "verified": True,
        "badge": "일반 리뷰",
    },
    {
        "id": 4,
        "author": "최*희",
        "rating": 5,
        "product_name": "[몬치치 백참] 아이보리 베어 토트백 키링 (가방 걸이용)",
        "content": "토트백 손잡이에 바로 걸 수 있어서 편하고 털도 몽글몽글 부드러워요. 보는 사람마다 어디서 샀냐고 물어봐요 💕",
        "date": "2026-09-25",
        "verified": True,
        "badge": "포토 리뷰",
    },
]

# 메모리 기반 리뷰 저장소 (새 리뷰 작성 시 즉시 반영)
REVIEWS_STORAGE = list(INITIAL_REVIEWS)

# 더미 상품 데이터 (첨부된 실제 제품 사진 100% 매칭)
PRODUCTS = [
    {
        "id": 1,
        "name": "[치무탄 정품] 핑크 토끼 페이스 인형 파우치 키링",
        "category": "POUCH & KEYRING",
        "price": "26,000",
        "original_price": "32,000",
        "badge": "BEST",
        "badge_color": "danger",
        "image": "/static/images/real_pink_rabbit.png",
        "description": "보송보송 핑크 토끼 귀와 딸기코가 사랑스러운 치무탄 오리지널 동전지갑 겸 인형 백참 키링입니다.",
    },
    {
        "id": 2,
        "name": "[치무탄 스트로베리] 레드 딸기 토끼 페이스 파우치",
        "category": "LIMITED",
        "price": "27,000",
        "original_price": "34,000",
        "badge": "NEW",
        "badge_color": "danger",
        "image": "/static/images/real_strawberry_rabbit.png",
        "description": "상큼한 레드 컬러에 초록색 딸기 꼭지와 씨앗 디테일이 돋보이는 한정판 스트로베리 토끼 파우치입니다.",
    },
    {
        "id": 3,
        "name": "[몬치치 클래식] 오리지널 레드 레더 체인 지갑",
        "category": "WALLET",
        "price": "22,000",
        "original_price": "28,000",
        "badge": "HOT",
        "badge_color": "danger",
        "image": "/static/images/real_monchhichi_red_wallet.png",
        "description": "빈티지한 레드 가죽 질감에 귀여운 몬치치 오리지널 캐릭터와 볼체인 키링이 달린 지퍼형 동전 지갑입니다.",
    },
    {
        "id": 4,
        "name": "[몬치치 백참] 아이보리 베어 토트백 키링 (가방 걸이용)",
        "category": "KEYRING",
        "price": "23,000",
        "original_price": "28,000",
        "badge": "TREND",
        "badge_color": "success",
        "image": "/static/images/real_bag_bear_keyring.png",
        "description": "토트백이나 에코백 손잡이에 바로 걸 수 있는 실버 체인이 달린 보송보송 아이보리 베어 키링입니다.",
    },
    {
        "id": 5,
        "name": "[치무탄 홈웨어] 포근한 핑크 체크 딸기 수면양말",
        "category": "LOUNGE",
        "price": "14,000",
        "original_price": "18,000",
        "badge": "COZY",
        "badge_color": "warning",
        "image": "/static/images/real_strawberry_sleep_socks.png",
        "description": "보들보들한 핑크 깅엄체크 극세사 퍼에 발목의 입체 딸기 니팅 자수와 화이트 보아퍼 밴딩이 더해진 보온 수면양말입니다.",
    },
    {
        "id": 6,
        "name": "[스페셜 화보] 몬치치 & 치무탄 3종 룩북 에디션",
        "category": "SET",
        "price": "75,000",
        "original_price": "95,000",
        "badge": "SPECIAL",
        "badge_color": "danger",
        "image": "/static/images/real_monchhichi_group.png",
        "description": "스트로베리 토끼, 핑크 치무탄, 가방 베어 키링 3종이 담긴 실물 촬영 공식 룩북 세트입니다.",
    },
]


@main_bp.route("/")
def index():
    """
    쇼핑몰 메인 페이지 뷰 함수
    - 몬치치 x VIBE 공식 캡슐 컬렉션 및 실시간 구매자 리뷰/별점 통계를 표시합니다.
    """
    display_products = PRODUCTS

    supabase = get_supabase_client()
    if supabase:
        try:
            # supabase-py 쿼리 빌더 인터페이스 사용
            response = supabase.table("products").select("*, product_images(image_url)").limit(8).execute()
            if response.data and len(response.data) > 0:
                has_monchhichi = any("몬치치" in str(item.get("name", "")) for item in response.data)
                if has_monchhichi:
                    display_products = []
                    for idx, row in enumerate(response.data):
                        img_url = None
                        if row.get("product_images") and len(row["product_images"]) > 0:
                            img_url = row["product_images"][0].get("image_url")
                        if not img_url:
                            img_url = PRODUCTS[idx % len(PRODUCTS)]["image"]

                        display_products.append({
                            "id": row.get("id", idx + 1),
                            "name": row.get("name", PRODUCTS[idx % len(PRODUCTS)]["name"]),
                            "category": "MONCHHICHI",
                            "price": f"{int(row.get('sale_price') or row.get('original_price', 30000)):,}",
                            "original_price": f"{int(row.get('original_price', 40000)):,}",
                            "badge": "BEST" if idx == 0 else "NEW",
                            "badge_color": "danger" if idx == 0 else "success",
                            "image": img_url,
                            "description": row.get("summary") or row.get("description") or PRODUCTS[idx % len(PRODUCTS)]["description"],
                        })
        except Exception as e:
            print(f"[안내] Supabase 'products' 테이블 조회 처리: {e}")

    # 별점 통계 계산
    total_reviews = len(REVIEWS_STORAGE)
    if total_reviews > 0:
        avg_rating = round(sum(r["rating"] for r in REVIEWS_STORAGE) / total_reviews, 1)
        rating_counts = {
            5: sum(1 for r in REVIEWS_STORAGE if r["rating"] == 5),
            4: sum(1 for r in REVIEWS_STORAGE if r["rating"] == 4),
            3: sum(1 for r in REVIEWS_STORAGE if r["rating"] == 3),
            2: sum(1 for r in REVIEWS_STORAGE if r["rating"] == 2),
            1: sum(1 for r in REVIEWS_STORAGE if r["rating"] == 1),
        }
        rating_percents = {
            k: int((v / total_reviews) * 100) for k, v in rating_counts.items()
        }
    else:
        avg_rating = 5.0
        rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        rating_percents = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

    review_stats = {
        "avg": avg_rating,
        "total": total_reviews,
        "counts": rating_counts,
        "percents": rating_percents,
    }

    cart_summary = get_cart_summary()

    return render_template(
        "index.html", 
        products=display_products,
        reviews=REVIEWS_STORAGE,
        review_stats=review_stats,
        cart=cart_summary
    )


def get_cart():
    """세션 내 장바구니 딕셔너리를 반환합니다."""
    if "cart" not in session or not isinstance(session["cart"], dict):
        session["cart"] = {}
    return session["cart"]


def get_cart_summary():
    """장바구니 아이템 목록, 총 수량, 총 금액을 계산합니다."""
    cart = get_cart()
    item_list = list(cart.values())
    total_count = sum(item.get("quantity", 1) for item in item_list)
    total_price = sum(item.get("raw_price", 0) * item.get("quantity", 1) for item in item_list)
    return {
        "items": item_list,
        "item_list": item_list,
        "total_count": total_count,
        "total_price": total_price,
        "total_price_formatted": f"{total_price:,}",
        "shipping_fee": 0,
    }


@main_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    """
    장바구니 상품 추가 핸들러
    - JSON 또는 일반 Form 요청 모두 지원
    """
    data = request.get_json(silent=True) or request.form
    product_id = str(data.get("product_id", "")).strip()

    # 등록된 상품 목록에서 대상 상품 검색
    target_product = next((p for p in PRODUCTS if str(p["id"]) == product_id), None)
    if not target_product:
        return jsonify({"success": False, "message": "해당 상품을 찾을 수 없습니다."}), 404

    cart = get_cart()
    raw_price = int(str(target_product["price"]).replace(",", "").replace("원", ""))

    if product_id in cart:
        cart[product_id]["quantity"] += 1
    else:
        cart[product_id] = {
            "id": target_product["id"],
            "name": target_product["name"],
            "price": target_product["price"],
            "raw_price": raw_price,
            "image": target_product["image"],
            "category": target_product.get("category", "POUCH"),
            "quantity": 1,
        }

    session.modified = True
    summary = get_cart_summary()

    if request.is_json:
        return jsonify({
            "success": True,
            "message": f"'{target_product['name']}' 상품이 장바구니에 담겼습니다! 🍓",
            "cart": summary
        })

    flash(f"'{target_product['name']}' 상품이 장바구니에 담겼습니다! 🍓", "success")
    return redirect(url_for("main.index"))


@main_bp.route("/cart/update", methods=["POST"])
def update_cart():
    """
    장바구니 수량 증가/감소/삭제 핸들러
    """
    data = request.get_json(silent=True) or request.form
    product_id = str(data.get("product_id", "")).strip()
    action = data.get("action", "").strip()  # 'increase', 'decrease', 'delete'

    cart = get_cart()
    if product_id in cart:
        if action == "increase":
            cart[product_id]["quantity"] += 1
        elif action == "decrease":
            cart[product_id]["quantity"] -= 1
            if cart[product_id]["quantity"] <= 0:
                del cart[product_id]
        elif action == "delete":
            del cart[product_id]

        session.modified = True

    summary = get_cart_summary()
    return jsonify({
        "success": True,
        "cart": summary,
        "message": "장바구니가 업데이트되었습니다."
    })


@main_bp.route("/cart/clear", methods=["POST"])
def clear_cart():
    """장바구니 전체 비우기"""
    session["cart"] = {}
    session.modified = True
    return jsonify({
        "success": True,
        "cart": get_cart_summary(),
        "message": "장바구니를 모두 비웠습니다."
    })


@main_bp.route("/cart/checkout", methods=["POST"])
def checkout():
    """주문 완료 시뮬레이션"""
    cart = get_cart()
    if not cart:
        return jsonify({"success": False, "message": "장바구니가 비어 있습니다."}), 400

    summary = get_cart_summary()
    session["cart"] = {}
    session.modified = True

    return jsonify({
        "success": True,
        "message": f"총 {summary['total_count']}개 상품({summary['total_price_formatted']}원)의 주문이 성공적으로 완료되었습니다! 🍓",
        "cart": get_cart_summary()
    })


@main_bp.route("/reviews/create", methods=["POST"])
def create_review():
    """
    구매자 리뷰 작성 처리 핸들러
    - 작성자명, 별점(1~5점), 대상 상품, 리뷰 내용을 받아 실시간 저장합니다.
    """
    author = request.form.get("author", "").strip() or "익명 구매자"
    # 이름 일부 마스킹 처리 (예: 홍길동 -> 홍*동)
    if len(author) > 1:
        masked_author = author[0] + "*" + author[2:] if len(author) > 2 else author[0] + "*"
    else:
        masked_author = author

    try:
        rating = int(request.form.get("rating", 5))
        if rating < 1 or rating > 5:
            rating = 5
    except ValueError:
        rating = 5

    product_name = request.form.get("product_name", "").strip() or "[몬치치 컬렉션] 베이비 블루 턱받이 인형 (20cm)"
    content = request.form.get("content", "").strip()

    if content:
        new_review = {
            "id": len(REVIEWS_STORAGE) + 1,
            "author": masked_author,
            "rating": rating,
            "product_name": product_name,
            "content": content,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "verified": True,
            "badge": "실구매자 리뷰",
        }
        # 최신 리뷰가 맨 앞에 오도록 추가
        REVIEWS_STORAGE.insert(0, new_review)
        flash("리뷰가 성공적으로 등록되었습니다! 소중한 후기 감사합니다.", "success")
    else:
        flash("리뷰 내용을 입력해주세요.", "warning")

    return redirect(url_for("main.index") + "#reviews")
