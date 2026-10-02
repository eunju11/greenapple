"""
주문 및 결제 라우트 모듈
주문서 작성, 배송지 입력, 더미 결제 및 주문 완료 처리를 담당합니다.
"""

import re
import secrets
from datetime import datetime
from functools import wraps
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from app.supabase_client import get_supabase_client, get_supabase_admin_client

# 주문 관련 기능을 담당할 블루프린트 생성
order_bp = Blueprint("order", __name__, url_prefix="/order")


def login_required(f):
    """
    로그인 필수 데코레이터
    로그인되지 않은 사용자의 접근 시 안내 메시지와 함께 로그인 화면으로 리다이렉트합니다.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or not session.get("user", {}).get("id"):
            flash("로그인이 필요한 서비스입니다.", "warning")
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated_function


def fetch_user_cart_items(user_id):
    """
    사용자의 장바구니 아이템 목록 및 가격/품절 정보를 조회합니다.
    - supabase-py를 사용하여 carts, product_options, products 테이블을 조인 조회합니다.
    - 반환값: (cart_items, total_subtotal, shipping_fee, final_total, has_out_of_stock)
    """
    admin_client = get_supabase_admin_client()
    supabase = admin_client or get_supabase_client()

    cart_items = []
    total_subtotal = 0
    has_out_of_stock = False

    if not supabase:
        return cart_items, 0, 0, 0, False

    try:
        # carts 테이블에서 사용자 장바구니 목록 조회
        res = (
            supabase.table("carts")
            .select(
                """
                id,
                quantity,
                product_id,
                option_id,
                product_options(id, option_name, option_value, color, size, stock_quantity, stock),
                products(id, name, sale_price, original_price, product_images(image_url))
                """
            )
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        raw_items = res.data or []
    except Exception as e:
        print(f"[오류] 장바구니 조회 실패: {e}")
        return [], 0, 0, 0, False

    for item in raw_items:
        cart_id = item.get("id")
        quantity = int(item.get("quantity") or 1)
        product_id = item.get("product_id")
        option_id = item.get("option_id")

        # 옵션 정보 파싱
        opt_data = item.get("product_options") or {}
        if isinstance(opt_data, list) and len(opt_data) > 0:
            opt_data = opt_data[0]
        elif not isinstance(opt_data, dict):
            opt_data = {}

        color = (opt_data.get("color") or "").strip()
        size = (opt_data.get("size") or "").strip()
        opt_name = (opt_data.get("option_name") or "").strip()
        opt_val = (opt_data.get("option_value") or "").strip()

        # 재고 수량 확인 (stock 또는 stock_quantity)
        raw_stock = opt_data.get("stock")
        if raw_stock is None:
            raw_stock = opt_data.get("stock_quantity", 0)
        stock_quantity = int(raw_stock or 0)

        # 품절 여부 판단 (stock <= 0)
        is_out_of_stock = stock_quantity <= 0
        if is_out_of_stock:
            has_out_of_stock = True

        # 옵션 텍스트 생성
        option_parts = []
        if color:
            option_parts.append(color)
        if size:
            option_parts.append(size)
        if not option_parts and opt_name and opt_val:
            option_parts.append(f"{opt_name}: {opt_val}")
        option_display = " / ".join(option_parts) if option_parts else "기본 옵션"

        # 상품 정보 파싱
        prod_data = item.get("products") or {}
        if isinstance(prod_data, list) and len(prod_data) > 0:
            prod_data = prod_data[0]
        elif not isinstance(prod_data, dict):
            prod_data = {}

        product_name = prod_data.get("name") or "상품"
        sale_price = int(prod_data.get("sale_price") or prod_data.get("original_price") or 0)

        # 상품 이미지 추출
        images = prod_data.get("product_images") or []
        image_url = images[0].get("image_url") if (isinstance(images, list) and len(images) > 0) else "/static/images/real_pink_rabbit.png"

        subtotal = sale_price * quantity
        total_subtotal += subtotal

        cart_items.append({
            "cart_id": cart_id,
            "product_id": product_id,
            "option_id": option_id,
            "product_name": product_name,
            "image_url": image_url,
            "option_display": option_display,
            "quantity": quantity,
            "unit_price": sale_price,
            "subtotal": subtotal,
            "stock_quantity": stock_quantity,
            "is_out_of_stock": is_out_of_stock,
        })

    # 배송비 계산 (총 상품금액 50,000원 이상 무료, 미만 3,000원)
    shipping_fee = 0 if total_subtotal >= 50000 else 3000
    final_total = total_subtotal + shipping_fee

    return cart_items, total_subtotal, shipping_fee, final_total, has_out_of_stock


@order_bp.route("/checkout", methods=["GET"])
@login_required
def checkout():
    """
    주문서 작성 페이지 (GET /order/checkout)
    - 로그인 필수 검증
    - 장바구니 비어있으면 /cart 리다이렉트
    - 품절(stock=0) 아이템이 하나라도 있으면 /cart 리다이렉트 및 안내 메시지
    - 장바구니 아이템 목록 표시 (수정 불가)
    - 배송지 입력 폼 및 금액 요약 렌더링
    """
    user_id = session.get("user", {}).get("id")

    cart_items, total_subtotal, shipping_fee, final_total, has_out_of_stock = fetch_user_cart_items(user_id)

    # 1. 장바구니 비어있으면 /cart 리다이렉트
    if not cart_items:
        flash("장바구니가 비어 있습니다.", "warning")
        return redirect(url_for("main.view_cart"))

    # 2. 품절(stock=0) 아이템이 하나라도 있으면 /cart 리다이렉트
    if has_out_of_stock:
        flash("품절된 상품이 있어 주문할 수 없습니다.", "danger")
        return redirect(url_for("main.view_cart"))

    # 3. profiles 테이블에서 로그인 사용자의 기본 정보 조회
    user_session = session.get("user", {})
    default_address = {
        "recipient_name": user_session.get("name", ""),
        "recipient_phone": user_session.get("phone", ""),
        "postal_code": "",
        "shipping_address": "",
        "shipping_detail_address": "",
    }

    supabase = get_supabase_admin_client() or get_supabase_client()
    if supabase and user_id:
        try:
            profile_res = (
                supabase.table("profiles")
                .select("*")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if profile_res.data and len(profile_res.data) > 0:
                p_row = profile_res.data[0]
                if p_row.get("full_name"):
                    default_address["recipient_name"] = p_row["full_name"]
                if p_row.get("phone"):
                    default_address["recipient_phone"] = p_row["phone"]
                if p_row.get("postal_code"):
                    default_address["postal_code"] = p_row["postal_code"]
                if p_row.get("shipping_address"):
                    default_address["shipping_address"] = p_row["shipping_address"]
                if p_row.get("shipping_detail_address"):
                    default_address["shipping_detail_address"] = p_row["shipping_detail_address"]
        except Exception as e:
            print(f"[안내] Supabase 프로필 조회 오류: {e}")

    return render_template(
        "order/checkout.html",
        cart_items=cart_items,
        total_subtotal=total_subtotal,
        shipping_fee=shipping_fee,
        final_total=final_total,
        default_address=default_address,
        item_count=len(cart_items),
    )


@order_bp.route("/api/shipping-address", methods=["GET"])
@login_required
def get_shipping_address():
    """
    마이페이지에 저장된 기본 배송지 정보 비동기 조회 API
    GET /order/api/shipping-address
    - profiles 테이블을 조회하여 수령인명, 연락처, 주소 정보를 JSON으로 반환합니다.
    """
    user_id = session.get("user", {}).get("id")
    user_session = session.get("user", {})

    address_info = {
        "recipient_name": user_session.get("name", ""),
        "recipient_phone": user_session.get("phone", ""),
        "postal_code": "",
        "shipping_address": "",
        "shipping_detail_address": "",
    }

    supabase = get_supabase_admin_client() or get_supabase_client()
    if supabase and user_id:
        try:
            profile_res = (
                supabase.table("profiles")
                .select("*")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if profile_res.data and len(profile_res.data) > 0:
                p_row = profile_res.data[0]
                address_info["recipient_name"] = p_row.get("full_name") or address_info["recipient_name"]
                address_info["recipient_phone"] = p_row.get("phone") or address_info["recipient_phone"]
                address_info["postal_code"] = p_row.get("postal_code") or ""
                address_info["shipping_address"] = p_row.get("shipping_address") or ""
                address_info["shipping_detail_address"] = p_row.get("shipping_detail_address") or ""
        except Exception as e:
            print(f"[오류] 프로필 배송지 조회 API 오류: {e}")

    # profiles 테이블에 상세 주소가 없는 경우 최근 orders 내역에서 fallback 조회 시도
    if supabase and not address_info["shipping_address"]:
        try:
            order_res = (
                supabase.table("orders")
                .select("recipient_name, recipient_phone, postal_code, shipping_address, shipping_detail_address")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if order_res.data and len(order_res.data) > 0:
                recent_order = order_res.data[0]
                if not address_info["recipient_name"]:
                    address_info["recipient_name"] = recent_order.get("recipient_name", "")
                if not address_info["recipient_phone"]:
                    address_info["recipient_phone"] = recent_order.get("recipient_phone", "")
                address_info["postal_code"] = recent_order.get("postal_code", "")
                address_info["shipping_address"] = recent_order.get("shipping_address", "")
                address_info["shipping_detail_address"] = recent_order.get("shipping_detail_address", "")
        except Exception as e:
            print(f"[안내] 이전 주문 배송지 조회 참고: {e}")

    return jsonify({
        "success": True,
        "data": address_info
    })


@order_bp.route("/create", methods=["POST"])
@order_bp.route("/checkout", methods=["POST"])
@login_required
def create_order():
    """
    주문 생성 핸들러 (POST /order/create 및 POST /order/checkout)
    
    처리 순서 (반드시 이 순서로):
    1. 장바구니 조회 + 재고 확인 (재고 부족 시 에러, 처리 중단, 아무 것도 쓰지 않음)
    2. 배송지 입력값 서버 측 재검증 (휴대폰 번호 패턴, 주소 최소 길이)
    3. 주문번호 생성: 'VF-' + 오늘날짜(YYYYMMDD) + '-' + 4자리 랜덤숫자 + 밀리초 타임스탬프 뒷 3자리
    4. orders 테이블에 INSERT (status='paid', paid_at=now())
    5. order_items INSERT (상품명, 색상, 사이즈, 가격 스냅샷)
    6. product_options.stock 차감 — 반드시 조건부 UPDATE 사용:
       UPDATE ... SET stock = stock - 수량 WHERE id = 옵션ID AND stock >= 수량
       영향받은 행이 0개면 "방금 재고가 소진되었습니다" 에러로 롤백 처리
    7. carts 아이템 DELETE
    8. /order/complete/<order_id> 리다이렉트
    """
    user_id = session.get("user", {}).get("id")

    # 관리자 키(service_role) 클라이언트 확보 (RLS 우회 및 트랜잭션 처리 필수)
    supabase = get_supabase_admin_client() or get_supabase_client()
    if not supabase:
        flash("데이터베이스 연결에 실패하여 주문을 진행할 수 없습니다.", "danger")
        return redirect(url_for("order.checkout"))

    # 1. 장바구니 조회 + 재고 확인 (재고 부족 시 에러, 처리 중단, 아무 것도 쓰지 않음)
    cart_items, total_subtotal, shipping_fee, final_total, has_out_of_stock = fetch_user_cart_items(user_id)

    if not cart_items:
        flash("장바구니가 비어 있어 주문을 진행할 수 없습니다.", "warning")
        return redirect(url_for("main.view_cart"))

    # 실시간 최신 재고 조회 및 부족 여부 확인
    for item in cart_items:
        opt_id = item.get("option_id")
        qty = item.get("quantity", 1)
        if opt_id:
            opt_chk = (
                supabase.table("product_options")
                .select("id, stock, stock_quantity")
                .eq("id", opt_id)
                .limit(1)
                .execute()
            )
            if not opt_chk.data or len(opt_chk.data) == 0:
                flash(f"'{item.get('product_name')}' 상품의 옵션 정보를 찾을 수 없습니다.", "danger")
                return redirect(url_for("main.view_cart"))

            current_stock = int(opt_chk.data[0].get("stock") or opt_chk.data[0].get("stock_quantity") or 0)
            if current_stock < qty:
                flash(f"'{item.get('product_name')}' 상품의 재고가 부족합니다 (남은 재고: {current_stock}개).", "danger")
                return redirect(url_for("main.view_cart"))
        else:
            if item.get("is_out_of_stock"):
                flash(f"'{item.get('product_name')}' 상품이 품절되어 주문할 수 없습니다.", "danger")
                return redirect(url_for("main.view_cart"))

    if has_out_of_stock:
        flash("품절된 상품이 있어 주문할 수 없습니다.", "danger")
        return redirect(url_for("main.view_cart"))

    # 2. 배송지 입력값 서버 측 재검증 (휴대폰 번호 패턴, 주소 최소 길이)
    recipient_name = request.form.get("recipient_name", "").strip()
    recipient_phone = request.form.get("recipient_phone", "").strip()
    postal_code = request.form.get("postal_code", "").strip() or "06236"
    shipping_address = request.form.get("shipping_address", "").strip()
    shipping_detail_address = request.form.get("shipping_detail_address", "").strip()
    shipping_memo = request.form.get("shipping_memo", "").strip()

    if not recipient_name:
        flash("수령인 이름을 입력해주세요.", "danger")
        return redirect(url_for("order.checkout"))

    # 휴대폰 번호 패턴 검증: 010-0000-0000 패턴
    phone_pattern = r"^010-\d{4}-\d{4}$"
    if not re.match(phone_pattern, recipient_phone):
        flash("휴대폰 번호는 010-0000-0000 형식으로 올바르게 입력해주세요.", "danger")
        return redirect(url_for("order.checkout"))

    # 배송 주소 최소 5자 이상 검증
    if len(shipping_address) < 5:
        flash("배송 주소는 최소 5자 이상 정확히 입력해주세요.", "danger")
        return redirect(url_for("order.checkout"))

    # 3. 주문번호 생성: 'VF-' + 오늘날짜(YYYYMMDD) + '-' + 4자리 랜덤숫자 + 밀리초 타임스탬프 뒷 3자리
    now = datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    random_digits = f"{secrets.randbelow(10000):04d}"
    millis_suffix = f"{int(now.microsecond / 1000):03d}"
    order_number = f"VF-{date_str}-{random_digits}{millis_suffix}"

    payment_method = request.form.get("payment_method", "card")
    now_iso = now.isoformat()

    order_id = None
    deducted_options = []  # 롤백 복구용 추적 리스트: [(option_id, qty, prev_stock)]
    deducted_products = []  # 롤백 복구용 상품 재고 추적 리스트: [(product_id, qty, prev_stock, prev_status)]

    try:
        # 4. orders 테이블에 INSERT (status='paid', paid_at=now())
        order_insert_payload = {
            "user_id": user_id,
            "order_number": order_number,
            "status": "paid",
            "total_amount": float(total_subtotal),
            "discount_amount": 0.0,
            "shipping_fee": float(shipping_fee),
            "final_amount": float(final_total),
            "recipient_name": recipient_name,
            "recipient_phone": recipient_phone,
            "postal_code": postal_code,
            "shipping_address": shipping_address,
            "shipping_detail_address": shipping_detail_address,
            "shipping_memo": shipping_memo,
            "payment_method": payment_method,
            "payment_status": "completed",
            "paid_at": now_iso,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        order_res = supabase.table("orders").insert(order_insert_payload).execute()
        if not order_res.data or len(order_res.data) == 0:
            raise Exception("주문 마스터 레코드 생성에 실패했습니다.")

        created_order = order_res.data[0]
        order_id = created_order.get("id")

        # 5. order_items INSERT (상품명, 색상, 사이즈, 가격 스냅샷)
        order_items_payload = []
        for item in cart_items:
            order_items_payload.append({
                "order_id": order_id,
                "product_id": item["product_id"],
                "option_id": item["option_id"],
                "product_name": item["product_name"],
                "option_description": item["option_display"],
                "quantity": item["quantity"],
                "unit_price": float(item["unit_price"]),
                "total_price": float(item["subtotal"]),
                "created_at": now_iso,
            })

        supabase.table("order_items").insert(order_items_payload).execute()

        # 6. product_options.stock 차감 — 반드시 조건부 UPDATE 사용:
        # UPDATE ... SET stock = stock - 수량 WHERE id = 옵션ID AND stock >= 수량
        # 영향받은 행이 0개면 "방금 재고가 소진되었습니다" 에러로 롤백 처리
        for item in cart_items:
            opt_id = item.get("option_id")
            qty = item.get("quantity", 1)
            if not opt_id:
                continue

            # 현재 최신 재고 조회
            cur_opt = (
                supabase.table("product_options")
                .select("id, stock, stock_quantity")
                .eq("id", opt_id)
                .limit(1)
                .execute()
            )
            if not cur_opt.data or len(cur_opt.data) == 0:
                raise ValueError("방금 재고가 소진되었습니다.")

            current_stock = int(cur_opt.data[0].get("stock") or cur_opt.data[0].get("stock_quantity") or 0)
            if current_stock < qty:
                raise ValueError("방금 재고가 소진되었습니다.")

            new_stock = current_stock - qty

            # 조건부 UPDATE 실행: WHERE id = 옵션ID AND stock >= 수량
            update_res = (
                supabase.table("product_options")
                .update({
                    "stock": new_stock,
                    "stock_quantity": new_stock,
                })
                .eq("id", opt_id)
                .gte("stock", qty)
                .execute()
            )

            # 영향받은 행이 0개면 동시성 경쟁 등으로 재고 부족 상태 발생
            if not update_res.data or len(update_res.data) == 0:
                raise ValueError("방금 재고가 소진되었습니다.")

            deducted_options.append((opt_id, qty, current_stock))

            # 부모 상품(products)의 총 재고 차감 및 상태 동기화
            prod_id = item.get("product_id")
            if prod_id:
                try:
                    p_res = supabase.table("products").select("stock_quantity, status").eq("id", prod_id).limit(1).execute()
                    if p_res.data and len(p_res.data) > 0:
                        cur_p_stock = int(p_res.data[0].get("stock_quantity") or 0)
                        new_p_stock = max(0, cur_p_stock - qty)
                        p_update_payload = {"stock_quantity": new_p_stock, "updated_at": now_iso}
                        if new_p_stock == 0:
                            all_opts = supabase.table("product_options").select("stock").eq("product_id", prod_id).execute()
                            if all(int(o.get("stock") or 0) <= 0 for o in (all_opts.data or [])):
                                p_update_payload["status"] = "sold_out"
                        supabase.table("products").update(p_update_payload).eq("id", prod_id).execute()
                        deducted_products.append((prod_id, qty, cur_p_stock, p_res.data[0].get("status")))
                except Exception as p_err:
                    print(f"[안내] 상품 총 재고 차감 처리: {p_err}")

        # 7. carts 아이템 DELETE
        supabase.table("carts").delete().eq("user_id", user_id).execute()

        # 세션 장바구니도 초기화
        session["cart"] = {}
        session.modified = True

        flash(f"주문이 성공적으로 완료되었습니다! (주문번호: {order_number})", "success")

        # 8. /order/complete/<order_id> 리다이렉트
        return redirect(url_for("order.order_complete", order_id=order_id))

    except Exception as e:
        print(f"[오류] 주문 처리 트랜잭션 오류: {e}")

        # 롤백 처리: 이미 차감된 옵션 재고 원상 복구
        for opt_id, qty, prev_stock in deducted_options:
            try:
                supabase.table("product_options").update({
                    "stock": prev_stock,
                    "stock_quantity": prev_stock,
                }).eq("id", opt_id).execute()
            except Exception as rb_opt_err:
                print(f"[롤백 오류] 옵션 재고 복구 실패: {rb_opt_err}")

        # 롤백 처리: 이미 차감된 부모 상품 재고 원상 복구
        for prod_id, qty, prev_stock, prev_status in deducted_products:
            try:
                supabase.table("products").update({
                    "stock_quantity": prev_stock,
                    "status": prev_status,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", prod_id).execute()
            except Exception as rb_prod_err:
                print(f"[롤백 오류] 상품 총재고 복구 실패: {rb_prod_err}")

        # 롤백 처리: 생성된 orders 레코드 및 관련 항목 삭제
        if order_id:
            try:
                supabase.table("order_items").delete().eq("order_id", order_id).execute()
                supabase.table("orders").delete().eq("id", order_id).execute()
            except Exception as rb_ord_err:
                print(f"[롤백 오류] 주문 데이터 롤백 실패: {rb_ord_err}")

        err_message = str(e)
        if "방금 재고가 소진되었습니다" in err_message:
            flash("방금 재고가 소진되었습니다. 장바구니를 확인해주세요.", "danger")
            return redirect(url_for("main.view_cart"))

        flash("결제 및 주문 처리 중 오류가 발생했습니다. 다시 시도해주세요.", "danger")
        return redirect(url_for("order.checkout"))


@order_bp.route("/complete/<order_id>", methods=["GET"])
@login_required
def order_complete(order_id):
    """
    주문 완료 화면 (GET /order/complete/<order_id>)
    - order_id (UUID 또는 주문번호)로 주문 및 주문 항목을 조회하여 완료 화면을 렌더링합니다.
    - 본인 주문이 맞는지 검증하며, 타인의 order_id 접근 시 403 오류 및 안내 메시지와 함께 메인으로 리다이렉트합니다.
    """
    user_id = session.get("user", {}).get("id")
    supabase = get_supabase_admin_client() or get_supabase_client()

    order_info = None
    order_items = []

    if supabase:
        try:
            # 먼저 order_id가 존재하는지 단독 조회하여 타인 주문인지 검사
            check_res = (
                supabase.table("orders")
                .select("id, user_id, order_number")
                .or_(f"id.eq.{order_id},order_number.eq.{order_id}")
                .limit(1)
                .execute()
            )

            if check_res.data and len(check_res.data) > 0:
                found_order = check_res.data[0]
                # 본인 주문이 아닌 경우 차단 (403 Forbidden 안내)
                if str(found_order.get("user_id")) != str(user_id):
                    flash("다른 사용자의 주문 정보에는 접근할 수 없습니다.", "danger")
                    return redirect(url_for("main.index")), 403

            # 본인 주문인 경우 전체 주문 상세 정보 조회
            res = (
                supabase.table("orders")
                .select("*")
                .or_(f"id.eq.{order_id},order_number.eq.{order_id}")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

            if res.data and len(res.data) > 0:
                order_info = res.data[0]
                target_order_id = order_info.get("id")

                # 주문 항목 조회
                items_res = (
                    supabase.table("order_items")
                    .select("*")
                    .eq("order_id", target_order_id)
                    .execute()
                )
                order_items = items_res.data or []
        except Exception as e:
            print(f"[오류] 주문 완료 조회 오류: {e}")

    if not order_info:
        flash("주문 정보를 찾을 수 없습니다.", "warning")
        return redirect(url_for("main.index")), 404

    return render_template(
        "order/complete.html",
        order=order_info,
        items=order_items
    )
