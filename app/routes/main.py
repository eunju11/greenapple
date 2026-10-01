"""
메인 라우트 모듈
쇼핑몰 메인 페이지 및 상품 목록 조회를 담당합니다.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import re
from app.supabase_client import get_supabase_client, get_supabase_admin_client
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


def get_product_by_id(product_id):
    """
    상품 ID로 상품 정보를 조회합니다.
    1. Supabase products 테이블 우선 조회
    2. 데이터가 없거나 연결 실패 시 PRODUCTS 더미 데이터에서 조회
    """
    supabase = get_supabase_client()
    if supabase:
        try:
            res = (
                supabase.table("products")
                .select("*, product_images(*)")
                .eq("id", product_id)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                row = res.data[0]
                images = row.get("product_images") or []
                main_image = images[0].get("image_url") if images else "/static/images/real_pink_rabbit.png"
                all_images = [img.get("image_url") for img in images if img.get("image_url")]
                if not all_images:
                    all_images = [main_image]

                orig_price = int(row.get("original_price") or 30000)
                sale_price = int(row.get("sale_price") or orig_price)
                discount_rate = int(((orig_price - sale_price) / orig_price) * 100) if orig_price > sale_price else 0

                return {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "summary": row.get("summary") or "",
                    "description": row.get("description") or "",
                    "original_price": orig_price,
                    "original_price_formatted": f"{orig_price:,}",
                    "sale_price": sale_price,
                    "sale_price_formatted": f"{sale_price:,}",
                    "discount_rate": discount_rate,
                    "stock_quantity": row.get("stock_quantity", 0),
                    "image": main_image,
                    "images": all_images,
                    "category": "컬렉션",
                    "badge": "BEST",
                    "badge_color": "danger",
                }
        except Exception as e:
            print(f"[안내] Supabase 단일 상품 조회: {e}")

    # Fallback: PRODUCTS 더미 데이터에서 검색
    target = next((p for p in PRODUCTS if str(p["id"]) == str(product_id)), None)
    if target:
        orig = int(str(target.get("original_price", "30000")).replace(",", "").replace("원", ""))
        sale = int(str(target.get("price", "25000")).replace(",", "").replace("원", ""))
        discount_rate = int(((orig - sale) / orig) * 100) if orig > sale else 0
        return {
            "id": target["id"],
            "name": target["name"],
            "summary": target.get("description", ""),
            "description": f"<p>{target.get('description', '')}</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다.</p>",
            "original_price": orig,
            "original_price_formatted": f"{orig:,}",
            "sale_price": sale,
            "sale_price_formatted": f"{sale:,}",
            "discount_rate": discount_rate,
            "stock_quantity": 50,
            "image": target["image"],
            "images": [target["image"]],
            "category": target.get("category", "KEYRING"),
            "badge": target.get("badge", "HOT"),
            "badge_color": target.get("badge_color", "danger"),
        }
    return None


@main_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    """
    상품 상세 페이지 뷰 함수 (GET /products/<product_id>)
    - Supabase에서 product_id로 상품 정보 조회
    - 상품 이미지, 이름, 가격(할인가/정가), 설명 표시
    - product_options 테이블에서 해당 상품의 색상 옵션 목록을 조회
    """
    product = get_product_by_id(product_id)
    if not product:
        return render_template("errors/404.html"), 404

    # 상품 옵션 조회: [{"id", "color", "size", "stock"}]
    options = []
    supabase = get_supabase_client()
    if supabase:
        try:
            res = (
                supabase.table("product_options")
                .select("id, color, size, stock_quantity")
                .eq("product_id", product_id)
                .order("id")
                .execute()
            )
            for item in res.data or []:
                options.append({
                    "id": item.get("id"),
                    "color": (item.get("color") or "").strip() or None,
                    "size": (item.get("size") or "").strip() or None,
                    "stock": int(item.get("stock_quantity") or 0),
                })
        except Exception as e:
            print(f"[오류] Supabase 옵션 조회 실패: {e}")

    # 색상/사이즈가 있는 상품은 둘 다 비어 있는 옛 옵션 행을 제외
    if any(o["color"] or o["size"] for o in options):
        options = [o for o in options if o["color"] or o["size"]]

    # 색상은 하나라도 있으면 노출, 사이즈는 'Free'만 있는 경우 선택 대상에서 제외
    colors = list(dict.fromkeys(o["color"] for o in options if o["color"]))
    real_sizes = {o["size"] for o in options if o["size"] and o["size"].lower() != "free"}
    has_color_option = len(colors) > 0
    has_size_option = len(real_sizes) > 0

    cart_summary = get_cart_summary()

    return render_template(
        "product_detail.html",
        product=product,
        colors=colors,
        options=options,
        has_color_option=has_color_option,
        has_size_option=has_size_option,
        cart=cart_summary,
    )


@main_bp.route("/api/products/<int:product_id>/sizes")
def get_product_sizes(product_id):
    """
    선택된 색상에 해당하는 사이즈 목록 및 재고 조회 API
    GET /api/products/<product_id>/sizes?color=<선택한 색상>
    - product_options 테이블에서 product_id + color로 필터링
    - [{"id": 1, "size": "Free", "stock": 20}] 형태의 JSON 배열 반환
    """
    color = request.args.get("color", "").strip()
    print(f"[디버그] /api/products/{product_id}/sizes 호출, color={color}")
    
    if not color:
        print(f"[디버그] color 파라미터 없음")
        return jsonify([]), 200

    sizes = []
    supabase = get_supabase_client()
    if supabase:
        try:
            # product_id와 color가 일치하는 모든 product_options 조회
            res = (
                supabase.table("product_options")
                .select("id, option_name, option_value, color, size, stock_quantity")
                .eq("product_id", product_id)
                .eq("color", color)
                .execute()
            )
            print(f"[디버그] product_id={product_id}, color='{color}' 조회 결과 개수: {len(res.data) if res.data else 0}")
            
            if res.data:
                for row in res.data:
                    print(f"[디버그] 옵션: id={row.get('id')}, name={row.get('option_name')}, color={row.get('color')}, size={row.get('size')}, stock={row.get('stock_quantity')}")
                    
                    # size 필드가 있으면 추가
                    if row.get("size"):
                        sizes.append({
                            "id": row.get("id"),
                            "size": row.get("size"),
                            "stock": int(row.get("stock_quantity", 0)),
                        })
                    # size 필드가 없으면 option_value를 사이즈로 사용
                    elif row.get("option_value"):
                        sizes.append({
                            "id": row.get("id"),
                            "size": row.get("option_value"),
                            "stock": int(row.get("stock_quantity", 0)),
                        })
        except Exception as e:
            print(f"[오류] Supabase 사이즈 조회 API 오류: {e}")

    # 옵션 데이터가 없을 경우 기본 테스트 데이터 fallback
    if not sizes:
        print(f"[디버그] 데이터 없음 → fallback 테스트 데이터 사용")
        sizes = [
            {"id": 1, "size": "Free", "stock": 15},
            {"id": 2, "size": "Free", "stock": 10},
            {"id": 3, "size": "Free", "stock": 8},
        ]

    print(f"[디버그] 반환할 사이즈 목록: {sizes}")
    return jsonify(sizes)


@main_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    """
    장바구니 상품 추가 핸들러 (POST /cart/add)
    
    요청 body:
    - product_option_id (필수): product_options 테이블의 ID
    - quantity (필수): 구매 수량 (1 이상)
    
    동작:
    1. 로그인 확인 → 미로그인 시 /auth/login으로 리다이렉트 또는 401 JSON 반환
    2. product_options에서 stock 조회
    3. 요청 수량 ≤ 현재 재고 확인
    4. carts 테이블에 upsert (같은 옵션이면 수량 누적)
    5. 누적 후 수량 ≤ 재고 확인
    6. 성공 시 JSON 반환 {"success": true, "message": "장바구니에 담겼습니다"}
    """
    # 1. 로그인 확인
    if "user" not in session:
        if request.is_json:
            return jsonify({
                "success": False,
                "message": "로그인이 필요합니다.",
                "redirect": url_for("auth.login_page")
            }), 401
        return redirect(url_for("auth.login_page"))

    user_id = session.get("user", {}).get("id")
    if not user_id:
        if request.is_json:
            return jsonify({
                "success": False,
                "message": "사용자 정보를 찾을 수 없습니다.",
            }), 400
        flash("사용자 정보를 찾을 수 없습니다.", "danger")
        return redirect(url_for("main.index"))

    # 2. 요청 파라미터 파싱
    data = request.get_json(silent=True) or request.form
    print(f"[디버그] 요청 데이터: {data}")
    try:
        product_option_id = int(data.get("product_option_id", 0))
        quantity = int(data.get("quantity", 1))
    except (ValueError, TypeError):
        print(f"[오류] product_option_id={data.get('product_option_id')}, quantity={data.get('quantity')} 파싱 실패")
        return jsonify({
            "success": False,
            "message": "product_option_id와 quantity는 정수여야 합니다."
        }), 400

    print(f"[디버그] product_option_id={product_option_id}, quantity={quantity}")

    if product_option_id <= 0 or quantity <= 0:
        print(f"[오류] product_option_id 또는 quantity가 0 이하: {product_option_id}, {quantity}")
        return jsonify({
            "success": False,
            "message": "product_option_id와 quantity는 0보다 커야 합니다."
        }), 400

    supabase = get_supabase_client()
    if not supabase:
        return jsonify({
            "success": False,
            "message": "데이터베이스 연결을 할 수 없습니다."
        }), 500

    # 3. product_options에서 stock_quantity 및 product_id 조회
    try:
        opt_res = (
            supabase.table("product_options")
            .select("id, product_id, stock_quantity")
            .eq("id", product_option_id)
            .limit(1)
            .execute()
        )
        if not opt_res.data or len(opt_res.data) == 0:
            return jsonify({
                "success": False,
                "message": "해당 상품 옵션을 찾을 수 없습니다."
            }), 404

        option_data = opt_res.data[0]
        current_stock = int(option_data.get("stock_quantity", 0))
        product_id = option_data.get("product_id")

    except Exception as e:
        print(f"[오류] product_options 조회 실패: {e}")
        return jsonify({
            "success": False,
            "message": "상품 정보 조회에 실패했습니다."
        }), 500

    # 4. 요청 수량이 현재 재고를 초과하는지 확인
    if quantity > current_stock:
        return jsonify({
            "success": False,
            "message": f"재고가 부족합니다(현재 {current_stock}개)"
        }), 400

    # 5. carts 테이블에서 기존 수량 조회
    try:
        cart_res = (
            supabase.table("carts")
            .select("quantity")
            .eq("user_id", user_id)
            .eq("product_id", product_id)
            .eq("option_id", product_option_id)
            .limit(1)
            .execute()
        )

        # 기존 수량이 있으면 누적, 없으면 요청 수량만 사용
        existing_quantity = 0
        if cart_res.data and len(cart_res.data) > 0:
            existing_quantity = int(cart_res.data[0].get("quantity", 0))
        
        new_quantity = existing_quantity + quantity

        # 누적 후 수량이 재고를 초과하는지 확인
        if new_quantity > current_stock:
            return jsonify({
                "success": False,
                "message": f"재고가 부족합니다(현재 {current_stock}개)"
            }), 400

        # 6. Upsert 수행: 같은 옵션이 있으면 수량 업데이트, 없으면 새로 추가
        supabase.table("carts").upsert({
            "user_id": user_id,
            "product_id": product_id,
            "option_id": product_option_id,
            "quantity": new_quantity,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }, on_conflict="user_id,product_id,option_id").execute()

    except Exception as e:
        print(f"[오류] carts 테이블 upsert 실패: {e}")
        return jsonify({
            "success": False,
            "message": "장바구니 추가에 실패했습니다."
        }), 500

    # 7. 성공 응답
    return jsonify({
        "success": True,
        "message": "장바구니에 담겼습니다"
    }), 200


@main_bp.route("/cart/<int:cart_id>", methods=["PATCH"])
def patch_cart_item(cart_id):
    """
    장바구니 수량 변경 핸들러 (PATCH /cart/<cart_id>)
    
    요청 body:
    - quantity (필수): 새로운 수량 (1 이상)
    
    동작:
    1. 로그인 확인
    2. cart_id로 carts 테이블에서 항목 조회
    3. 현재 로그인 사용자 확인 (본인 소유 여부)
    4. quantity 검증 (1 이상)
    5. product_options에서 재고 확인
    6. quantity ≤ stock 확인
    7. UPDATE 수행
    8. 성공 시 새 소계(subtotal) 반환
    """
    # 1. 로그인 확인
    if "user" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다.",
            "redirect": url_for("auth.login_page")
        }), 401

    user_id = session.get("user", {}).get("id")
    if not user_id:
        return jsonify({
            "success": False,
            "message": "사용자 정보를 찾을 수 없습니다.",
        }), 400

    # 요청 파라미터 파싱
    data = request.get_json(silent=True) or request.form
    try:
        new_quantity = int(data.get("quantity", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "quantity는 정수여야 합니다."
        }), 400

    if new_quantity < 1:
        return jsonify({
            "success": False,
            "message": "수량은 1 이상이어야 합니다."
        }), 400

    supabase = get_supabase_client()
    if not supabase:
        return jsonify({
            "success": False,
            "message": "데이터베이스 연결을 할 수 없습니다."
        }), 500

    # 2. cart_id로 carts 테이블에서 항목 조회
    try:
        cart_res = (
            supabase.table("carts")
            .select("id, user_id, product_id, option_id, quantity")
            .eq("id", cart_id)
            .limit(1)
            .execute()
        )
        if not cart_res.data or len(cart_res.data) == 0:
            return jsonify({
                "success": False,
                "message": "해당 장바구니 항목을 찾을 수 없습니다."
            }), 404

        cart_item = cart_res.data[0]
    except Exception as e:
        print(f"[오류] carts 테이블 조회 실패: {e}")
        return jsonify({
            "success": False,
            "message": "장바구니 조회에 실패했습니다."
        }), 500

    # 3. 현재 로그인 사용자가 본인 소유인지 확인
    if cart_item.get("user_id") != user_id:
        return jsonify({
            "success": False,
            "message": "다른 사용자의 장바구니 항목에 접근할 수 없습니다."
        }), 403

    # 4. product_options에서 재고 확인
    try:
        option_id = cart_item.get("option_id")
        opt_res = (
            supabase.table("product_options")
            .select("stock")
            .eq("id", option_id)
            .limit(1)
            .execute()
        )
        if not opt_res.data or len(opt_res.data) == 0:
            return jsonify({
                "success": False,
                "message": "해당 상품 옵션을 찾을 수 없습니다."
            }), 404

        current_stock = int(opt_res.data[0].get("stock", 0))
    except Exception as e:
        print(f"[오류] product_options 조회 실패: {e}")
        return jsonify({
            "success": False,
            "message": "상품 정보 조회에 실패했습니다."
        }), 500

    # 5. 변경하려는 수량이 재고를 초과하는지 확인
    if new_quantity > current_stock:
        return jsonify({
            "success": False,
            "message": f"재고가 부족합니다(현재 {current_stock}개)"
        }), 400

    # 6. UPDATE 수행
    try:
        supabase.table("carts").update({
            "quantity": new_quantity,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", cart_id).execute()
    except Exception as e:
        print(f"[오류] carts 테이블 업데이트 실패: {e}")
        return jsonify({
            "success": False,
            "message": "장바구니 업데이트에 실패했습니다."
        }), 500

    # 7. 새 소계 계산 (product와 product_options에서 가격 조회)
    try:
        product_id = cart_item.get("product_id")
        
        # products 테이블에서 판매가 조회
        prod_res = (
            supabase.table("products")
            .select("sale_price, original_price")
            .eq("id", product_id)
            .limit(1)
            .execute()
        )
        
        if not prod_res.data or len(prod_res.data) == 0:
            return jsonify({
                "success": False,
                "message": "상품 정보를 찾을 수 없습니다."
            }), 404
        
        prod = prod_res.data[0]
        base_price = int(prod.get("sale_price") or prod.get("original_price") or 0)
        
        # product_options에서 추가 가격 조회
        opt_price_res = (
            supabase.table("product_options")
            .select("additional_price")
            .eq("id", option_id)
            .limit(1)
            .execute()
        )
        
        additional_price = 0
        if opt_price_res.data and len(opt_price_res.data) > 0:
            additional_price = int(opt_price_res.data[0].get("additional_price", 0))
        
        # 소계 계산
        unit_price = base_price + additional_price
        subtotal = unit_price * new_quantity
        
    except Exception as e:
        print(f"[오류] 가격 정보 조회 실패: {e}")
        # 가격 조회 실패해도 업데이트는 완료되었으므로 성공 응답
        return jsonify({
            "success": True,
            "message": "수량이 변경되었습니다.",
            "new_quantity": new_quantity
        }), 200

    # 8. 성공 응답 (새 소계 포함)
    return jsonify({
        "success": True,
        "message": "수량이 변경되었습니다.",
        "new_quantity": new_quantity,
        "subtotal": subtotal,
        "subtotal_formatted": f"{subtotal:,}원"
    }), 200


@main_bp.route("/cart/<int:cart_id>", methods=["DELETE"])
def delete_cart_item(cart_id):
    """
    장바구니 아이템 삭제 핸들러 (DELETE /cart/<cart_id>)
    
    동작:
    1. 로그인 확인
    2. cart_id로 carts 테이블에서 항목 조회
    3. 현재 로그인 사용자 확인 (본인 소유 여부)
    4. DELETE 수행
    5. 성공 응답
    """
    # 1. 로그인 확인
    if "user" not in session:
        return jsonify({
            "success": False,
            "message": "로그인이 필요합니다.",
            "redirect": url_for("auth.login_page")
        }), 401

    user_id = session.get("user", {}).get("id")
    if not user_id:
        return jsonify({
            "success": False,
            "message": "사용자 정보를 찾을 수 없습니다.",
        }), 400

    supabase = get_supabase_client()
    if not supabase:
        return jsonify({
            "success": False,
            "message": "데이터베이스 연결을 할 수 없습니다."
        }), 500

    # 2. cart_id로 carts 테이블에서 항목 조회
    try:
        cart_res = (
            supabase.table("carts")
            .select("id, user_id")
            .eq("id", cart_id)
            .limit(1)
            .execute()
        )
        if not cart_res.data or len(cart_res.data) == 0:
            return jsonify({
                "success": False,
                "message": "해당 장바구니 항목을 찾을 수 없습니다."
            }), 404

        cart_item = cart_res.data[0]
    except Exception as e:
        print(f"[오류] carts 테이블 조회 실패: {e}")
        return jsonify({
            "success": False,
            "message": "장바구니 조회에 실패했습니다."
        }), 500

    # 3. 현재 로그인 사용자가 본인 소유인지 확인
    if cart_item.get("user_id") != user_id:
        return jsonify({
            "success": False,
            "message": "다른 사용자의 장바구니 항목에 접근할 수 없습니다."
        }), 403

    # 4. DELETE 수행
    try:
        supabase.table("carts").delete().eq("id", cart_id).execute()
    except Exception as e:
        print(f"[오류] carts 테이블 삭제 실패: {e}")
        return jsonify({
            "success": False,
            "message": "장바구니 항목 삭제에 실패했습니다."
        }), 500

    # 5. 성공 응답
    return jsonify({
        "success": True,
        "message": "장바구니에서 삭제되었습니다."
    }), 200


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


@main_bp.route("/cart", methods=["GET"])
def view_cart():
    """
    장바구니 페이지 뷰 (GET /cart)
    
    동작:
    1. 로그인 확인 → 미로그인 시 로그인 페이지로 리다이렉트
    2. carts 테이블에서 현재 사용자의 모든 항목 조회
    3. 각 항목과 product_options, products JOIN
    4. 상품명, 색상, 사이즈, 수량, 단가, 소계 구성
    5. 품절(stock=0) 여부 확인
    6. 배송비 계산 (합계 50,000원 미만 3,000원, 이상 무료)
    """
    # 1. 로그인 확인
    if "user" not in session:
        flash("장바구니를 보려면 로그인해주세요.", "warning")
        return redirect(url_for("auth.login_page"))

    user_id = session.get("user", {}).get("id")
    if not user_id:
        flash("사용자 정보를 찾을 수 없습니다.", "danger")
        return redirect(url_for("auth.login_page"))

    supabase = get_supabase_client()
    if not supabase:
        flash("데이터베이스 연결을 할 수 없습니다.", "danger")
        return redirect(url_for("main.index"))

    # 2. carts 테이블에서 현재 사용자의 모든 항목 조회
    try:
        cart_res = (
            supabase.table("carts")
            .select(
                """
                id,
                quantity,
                product_id,
                option_id,
                product_options(option_name, option_value, color, size, stock_quantity),
                products(name, sale_price, original_price)
                """
            )
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        cart_items_raw = cart_res.data if cart_res.data else []
    except Exception as e:
        print(f"[오류] 장바구니 조회 실패: {e}")
        flash("장바구니 조회에 실패했습니다.", "danger")
        return redirect(url_for("main.index"))

    # 3. 장바구니 아이템 구성
    cart_items = []
    total_subtotal = 0
    has_out_of_stock = False

    for item in cart_items_raw:
        cart_id = item.get("id")
        quantity = item.get("quantity", 1)
        
        # product_options에서 옵션 정보 추출
        option_data = item.get("product_options", {})
        if isinstance(option_data, list) and len(option_data) > 0:
            option_data = option_data[0]
        
        option_name = option_data.get("option_name", "")
        option_value = option_data.get("option_value", "")
        color = option_data.get("color", "")
        size = option_data.get("size", "")
        stock_quantity = option_data.get("stock_quantity", 0)
        
        # products에서 상품 정보 추출
        product_data = item.get("products", {})
        if isinstance(product_data, list) and len(product_data) > 0:
            product_data = product_data[0]
        
        product_name = product_data.get("name", "상품")
        sale_price = float(product_data.get("sale_price", 0))
        
        # 소계 계산
        subtotal = sale_price * quantity
        total_subtotal += subtotal
        
        # 품절 여부
        is_out_of_stock = stock_quantity <= 0
        if is_out_of_stock:
            has_out_of_stock = True
        
        # 색상/사이즈 표시
        option_display = ""
        if color:
            option_display = color
        if size:
            option_display += f" / {size}" if option_display else size
        if option_name and not option_display:
            option_display = f"{option_name}: {option_value}"
        
        cart_items.append({
            "id": cart_id,
            "product_name": product_name,
            "option_display": option_display,
            "quantity": quantity,
            "unit_price": sale_price,
            "subtotal": subtotal,
            "is_out_of_stock": is_out_of_stock,
            "stock_quantity": stock_quantity,
        })

    # 4. 배송비 계산
    shipping_fee = 0 if total_subtotal >= 50000 else 3000
    final_total = total_subtotal + shipping_fee

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_subtotal=total_subtotal,
        shipping_fee=shipping_fee,
        final_total=final_total,
        has_out_of_stock=has_out_of_stock,
        cart_count=len(cart_items),
    )


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


def login_required(f):
    """
    로그인 필수 데코레이터
    로그인되지 않은 사용자의 접근 시 안내 메시지와 함께 로그인 화면으로 리다이렉트합니다.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("로그인이 필요한 서비스입니다. 카카오톡으로 간편 로그인해주세요.", "warning")
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated_function


@main_bp.route("/mypage", methods=["GET", "POST"])
@login_required
def mypage():
    """
    마이페이지 뷰 함수 (GET /mypage)
    - 탭1: 내 정보 (이름, 이메일, 기본 배송지 표시 및 정보 수정 폼)
    - 탭2: 주문 내역 (안내 문구)
    - 탭3: 환불 내역 (안내 문구)
    - profiles 테이블에서 로그인 사용자 정보를 조회하여 표시합니다.
    """
    current_user = session.get("user", {})
    user_email = current_user.get("email", "")

    supabase = get_supabase_client()
    profile_data = {
        "full_name": current_user.get("name", ""),
        "email": user_email,
        "phone": current_user.get("phone", ""),
        "postal_code": "",
        "shipping_address": "",
        "shipping_detail_address": "",
        "grade": current_user.get("grade", "BRONZE"),
        "role": "customer",
        "provider": current_user.get("provider", "email"),
    }

    # Supabase profiles 테이블에서 사용자 최신 정보 조회
    if supabase and user_email:
        try:
            res = supabase.table("profiles").select("*").eq("email", user_email).limit(1).execute()
            if res.data and len(res.data) > 0:
                user_row = res.data[0]
                profile_data["full_name"] = user_row.get("full_name") or profile_data["full_name"]
                profile_data["email"] = user_row.get("email") or profile_data["email"]
                profile_data["phone"] = user_row.get("phone") or profile_data["phone"]
                profile_data["postal_code"] = user_row.get("postal_code") or ""
                profile_data["shipping_address"] = user_row.get("shipping_address") or ""
                profile_data["shipping_detail_address"] = user_row.get("shipping_detail_address") or ""
                profile_data["grade"] = user_row.get("grade") or profile_data["grade"]
                if user_row.get("provider"):
                    profile_data["provider"] = user_row.get("provider")
        except Exception as e:
            print(f"[안내] Supabase 프로필 조회: {e}")

    # POST 요청: 내 정보 및 배송지 정보 수정 처리
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip() or profile_data["full_name"]
        phone = request.form.get("phone", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        shipping_address = request.form.get("shipping_address", "").strip()
        shipping_detail_address = request.form.get("shipping_detail_address", "").strip()

        # 세션 정보 갱신
        session["user"]["name"] = full_name
        session["user"]["phone"] = phone
        session.modified = True

        # profiles 테이블 업데이트 시도
        if supabase and user_email:
            try:
                update_payload = {
                    "full_name": full_name,
                    "phone": phone,
                    "postal_code": postal_code,
                    "shipping_address": shipping_address,
                    "shipping_detail_address": shipping_detail_address,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                # 컬럼 미존재 에러 방지를 위해 단계별 저장 시도
                try:
                    supabase.table("profiles").update(update_payload).eq("email", user_email).execute()
                except Exception:
                    basic_payload = {"full_name": full_name, "phone": phone}
                    supabase.table("profiles").update(basic_payload).eq("email", user_email).execute()
            except Exception as e:
                print(f"[안내] Supabase 프로필 수정: {e}")

        flash("회원 정보 및 배송지 정보가 성공적으로 저장되었습니다. 🍓", "success")
        return redirect(url_for("main.mypage"))

    return render_template("mypage.html", profile=profile_data)


@main_bp.route("/mypage/change-password", methods=["POST"])
@login_required
def change_password():
    """
    비밀번호 변경 처리 핸들러 (POST /mypage/change-password)
    - 이메일/비밀번호 가입 회원만 비밀번호 변경 가능
    - 기존 비밀번호 검증 (Supabase sign_in_with_password 시도)
    - 새 비밀번호 일치 확인 및 강도 유효성 검사 (최소 8자, 영문/숫자/특수문자 조합)
    - 기존 비밀번호와 새 비밀번호 동일 여부 체크
    - Supabase update_user_by_id()를 통한 비밀번호 변경
    """
    current_user = session.get("user", {})
    user_email = current_user.get("email", "")
    provider = current_user.get("provider", "email")

    # 소셜 로그인 사용자는 비밀번호 변경 불가
    if provider in ["kakao", "microsoft", "google"]:
        flash("소셜 로그인 계정은 비밀번호 변경을 지원하지 않습니다.", "warning")
        return redirect(url_for("main.mypage"))

    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    # 1. 필수 입력 필드 검증
    if not current_password or not new_password or not confirm_password:
        flash("현재 비밀번호와 새 비밀번호를 모두 입력해주세요.", "danger")
        return redirect(url_for("main.mypage"))

    # 2. 새 비밀번호와 기존 비밀번호 동일 여부 검증
    if current_password == new_password:
        flash("새로운 비밀번호가 현재 비밀번호와 동일합니다.", "danger")
        return redirect(url_for("main.mypage"))

    # 3. 새 비밀번호 확인 일치 검증
    if new_password != confirm_password:
        flash("새 비밀번호와 확인용 비밀번호가 일치하지 않습니다.", "danger")
        return redirect(url_for("main.mypage"))

    # 4. 새 비밀번호 유효성 조건 검증 (최소 8자 이상, 영문 + 숫자 + 특수문자 조합)
    if len(new_password) < 8:
        flash("새 비밀번호는 최소 8자 이상이어야 합니다.", "danger")
        return redirect(url_for("main.mypage"))

    has_letter = bool(re.search(r"[A-Za-z]", new_password))
    has_digit = bool(re.search(r"\d", new_password))
    has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password))

    if not (has_letter and has_digit and has_special):
        flash("새 비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다.", "danger")
        return redirect(url_for("main.mypage"))

    supabase = get_supabase_client()
    if not supabase:
        flash("인증 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.", "danger")
        return redirect(url_for("main.mypage"))

    # 5. 기존 비밀번호 검증 (Supabase 재로그인 방식으로 확인)
    user_id = current_user.get("id")
    try:
        sign_in_res = supabase.auth.sign_in_with_password({
            "email": user_email,
            "password": current_password
        })
        if not sign_in_res or not sign_in_res.user:
            flash("현재 비밀번호가 일치하지 않습니다.", "danger")
            return redirect(url_for("main.mypage"))
        # 실제 auth.users의 고유 ID 획득
        user_id = sign_in_res.user.id
    except Exception as auth_err:
        err_msg = str(auth_err).lower()
        if "invalid" in err_msg or "credential" in err_msg or "grant" in err_msg:
            flash("현재 비밀번호가 일치하지 않습니다.", "danger")
            return redirect(url_for("main.mypage"))
        print(f"[안내] Supabase 인증 확인 중: {auth_err}")
        flash("현재 비밀번호가 일치하지 않습니다.", "danger")
        return redirect(url_for("main.mypage"))

    # 6. Supabase update_user_by_id()를 통한 비밀번호 갱신
    admin_client = get_supabase_admin_client() or supabase
    try:
        if hasattr(admin_client.auth, "admin") and hasattr(admin_client.auth.admin, "update_user_by_id"):
            admin_client.auth.admin.update_user_by_id(
                uid=str(user_id),
                attributes={"password": new_password}
            )
        else:
            # 기본 클라이언트 update_user 사용
            admin_client.auth.update_user({"password": new_password})

        flash("비밀번호가 변경되었습니다. 🍓", "success")
        return redirect(url_for("main.mypage"))
    except Exception as update_err:
        print(f"[오류] Supabase 비밀번호 변경 실패: {update_err}")
        flash(f"비밀번호 변경 처리 중 오류가 발생했습니다: {update_err}", "danger")
        return redirect(url_for("main.mypage"))


