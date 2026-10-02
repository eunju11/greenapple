"""
쇼핑몰 관리자 라우트 모듈
- 구매자 수요를 반영한 인기 상품 분석 및 통계
- 회원 정보 및 등급/권한 관리
- 주문자 정보 및 주문/배송 상태 관리
- 대시보드 KPI 및 상태 변경 처리
"""

from functools import wraps
from datetime import datetime, timedelta
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

# 관리자 기능을 담당할 블루프린트 생성
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """
    관리자 권한 필수 데코레이터
    1. 로그인 여부 확인
    2. 사용자 프로필에서 role='admin' 확인
    3. 만약 시스템에 등록된 관리자가 하나도 없으면 현재 사용자를 자동으로 관리자로 승격 처리
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or not session.get("user", {}).get("id"):
            flash("관리자 로그인이 필요한 서비스입니다.", "warning")
            return redirect(url_for("auth.login_page"))

        user_id = session.get("user", {}).get("id")
        supabase = get_supabase_admin_client() or get_supabase_client()

        if supabase and user_id:
            try:
                # 현재 사용자의 role 확인
                res = (
                    supabase.table("profiles")
                    .select("id, role, full_name, email")
                    .eq("id", user_id)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    current_role = res.data[0].get("role", "customer")
                    if current_role == "admin":
                        session["user"]["role"] = "admin"
                        session.modified = True
                        return f(*args, **kwargs)

                # 만약 시스템에 admin이 한 명도 없는 경우, 현재 접속자를 최초 관리자로 승격
                admin_check = (
                    supabase.table("profiles")
                    .select("id")
                    .eq("role", "admin")
                    .limit(1)
                    .execute()
                )
                if not admin_check.data or len(admin_check.data) == 0:
                    supabase.table("profiles").update({"role": "admin"}).eq("id", user_id).execute()
                    session["user"]["role"] = "admin"
                    session.modified = True
                    flash("🍓 최초 관리자 권한이 부여되었습니다. 환영합니다!", "success")
                    return f(*args, **kwargs)

            except Exception as e:
                print(f"[안내] 관리자 권한 확인 오류: {e}")

        # 세션에 admin 역할이 있는 경우 허용
        if session.get("user", {}).get("role") == "admin":
            return f(*args, **kwargs)

        flash("관리자 권한이 없는 계정입니다. 관리자 계정으로 로그인해주세요.", "danger")
        return redirect(url_for("admin.access_denied"))

    return decorated_function


@admin_bp.route("/access-denied")
def access_denied():
    """관리자 권한 없음 안내 및 데모 관리자 승격 버튼 제공 페이지"""
    return render_template("admin/access_denied.html")


@admin_bp.route("/promote-me", methods=["POST"])
def promote_me():
    """
    개발 및 테스트 편의를 위해 현재 로그인된 사용자를 관리자로 승격시키는 엔드포인트
    """
    if "user" not in session or not session.get("user", {}).get("id"):
        flash("먼저 로그인해주세요.", "warning")
        return redirect(url_for("auth.login_page"))

    user_id = session.get("user", {}).get("id")
    supabase = get_supabase_admin_client() or get_supabase_client()

    if supabase and user_id:
        try:
            supabase.table("profiles").update({"role": "admin"}).eq("id", user_id).execute()
            session["user"]["role"] = "admin"
            session.modified = True
            flash("🍓 관리자(admin) 권한으로 성공적으로 승격되었습니다!", "success")
            return redirect(url_for("admin.dashboard"))
        except Exception as e:
            print(f"[오류] 관리자 승격 실패: {e}")
            flash("관리자 권한 변경에 실패했습니다.", "danger")

    return redirect(url_for("main.index"))


def compute_daily_analytics(orders, days=7):
    """
    지정된 기간(days) 동안의 일별 매출액 및 주문 건수 통계 산출
    """
    today = datetime.utcnow().date()
    date_list = [(today - timedelta(days=i)) for i in range(days - 1, -1, -1)]

    stats = {
        d.strftime("%Y-%m-%d"): {
            "date": d.strftime("%Y-%m-%d"),
            "label": d.strftime("%m/%d"),
            "revenue": 0,
            "orders": 0
        }
        for d in date_list
    }

    total_rev = 0
    total_cnt = 0

    for o in orders:
        c = o.get("created_at", "")
        if c:
            d_str = c[:10]
            if d_str in stats:
                st = o.get("status")
                if st in ["paid", "preparing", "shipped", "delivered"]:
                    amt = int(float(o.get("final_amount") or 0))
                    stats[d_str]["revenue"] += amt
                    stats[d_str]["orders"] += 1
                    total_rev += amt
                    total_cnt += 1

    sorted_dates = sorted(stats.keys())
    labels = [stats[d]["label"] for d in sorted_dates]
    full_dates = sorted_dates
    revenues = [stats[d]["revenue"] for d in sorted_dates]
    orders_counts = [stats[d]["orders"] for d in sorted_dates]
    avg_order_value = int(total_rev / total_cnt) if total_cnt > 0 else 0

    return {
        "labels": labels,
        "dates": full_dates,
        "revenues": revenues,
        "orders": orders_counts,
        "summary": {
            "days": days,
            "total_revenue": total_rev,
            "total_revenue_formatted": f"{total_rev:,}원",
            "total_orders": total_cnt,
            "avg_order_value": avg_order_value,
            "avg_order_value_formatted": f"{avg_order_value:,}원",
        }
    }


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """
    관리자 메인 대시보드
    - 1. 구매자 수요 반영 인기 상품 통계 (Top Sellers, 장바구니 담김 수, 실시간 수요 지수)
    - 2. 회원 정보 목록 (등급, 총 지출액, 주문 수, 권한)
    - 3. 주문자 및 주문 관리 (주문 번호, 주문자/수령인 정보, 주문 상품, 결제/배송 상태)
    """
    supabase = get_supabase_admin_client() or get_supabase_client()

    # 1. 원본 데이터 조회
    products = []
    orders = []
    profiles = []
    order_items = []
    cart_items = []

    if supabase:
        try:
            # 상품 및 옵션, 이미지 조회
            prod_res = (
                supabase.table("products")
                .select("*, product_images(image_url), product_options(id, color, size, stock, stock_quantity)")
                .order("id")
                .execute()
            )
            products = prod_res.data or []

            # 주문 및 주문자(profiles), 주문 품목(order_items) JOIN 조회
            orders_res = (
                supabase.table("orders")
                .select("*, profiles(id, full_name, email, phone, grade), order_items(*)")
                .order("created_at", desc=True)
                .execute()
            )
            orders = orders_res.data or []

            # 전체 회원 프로필 조회
            profiles_res = (
                supabase.table("profiles")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            profiles = profiles_res.data or []

            # 주문 항목 전체 조회 (수요 집계용)
            items_res = supabase.table("order_items").select("*").execute()
            order_items = items_res.data or []

            # 장바구니 항목 조회 (잠재적 수요 지표)
            carts_res = supabase.table("carts").select("product_id, quantity").execute()
            cart_items = carts_res.data or []

        except Exception as e:
            print(f"[오류] 관리자 데이터 로드 실패: {e}")

    # =========================================================================
    # A. KPI 핵심 요약 지표 계산
    # =========================================================================
    total_revenue = sum(float(o.get("final_amount") or 0) for o in orders if o.get("status") in ["paid", "preparing", "shipped", "delivered"])
    total_orders_count = len(orders)
    total_members_count = len(profiles)

    # =========================================================================
    # B. 구매자 수요를 반영한 인기 제품 분석 (Demand Analytics)
    # =========================================================================
    # 1) 상품별 판매량 및 매출액 집계 (order_items 기준)
    sales_by_product = {}   # {product_id: {"qty": 0, "revenue": 0, "order_ids": set()}}
    for oi in order_items:
        pid = oi.get("product_id")
        if pid:
            if pid not in sales_by_product:
                sales_by_product[pid] = {"qty": 0, "revenue": 0, "order_ids": set()}
            sales_by_product[pid]["qty"] += int(oi.get("quantity") or 1)
            sales_by_product[pid]["revenue"] += float(oi.get("total_price") or 0)
            if oi.get("order_id"):
                sales_by_product[pid]["order_ids"].add(oi["order_id"])

    # 2) 상품별 장바구니 담김 수 집계 (현재 장바구니에 보관된 잠재 수요)
    cart_count_by_product = {}
    for ci in cart_items:
        pid = ci.get("product_id")
        if pid:
            cart_count_by_product[pid] = cart_count_by_product.get(pid, 0) + int(ci.get("quantity") or 1)

    # 3) 상품 객체와 결합하여 종합 수요 지수(Demand Score) 산출
    popular_products = []
    low_stock_count = 0

    for prod in products:
        pid = prod["id"]
        sales_info = sales_by_product.get(pid, {"qty": 0, "revenue": 0, "order_ids": set()})
        sold_qty = sales_info["qty"]
        revenue = sales_info["revenue"]
        order_freq = len(sales_info["order_ids"])
        cart_qty = cart_count_by_product.get(pid, 0)
        view_cnt = int(prod.get("view_count") or 0)

        # 재고 수량 종합 (옵션 재고의 합 또는 상품 테이블의 stock_quantity)
        options = prod.get("product_options") or []
        if options:
            total_stock = sum(int(opt.get("stock") or opt.get("stock_quantity") or 0) for opt in options)
        else:
            total_stock = int(prod.get("stock_quantity") or 0)

        if total_stock <= 5:
            low_stock_count += 1

        # 대표 이미지 추출
        images = prod.get("product_images") or []
        img_url = images[0].get("image_url") if (isinstance(images, list) and len(images) > 0) else "/static/images/real_pink_rabbit.png"

        # 수요 지수(Demand Score) 산출 공식:
        # (실제 판매수량 * 15) + (장바구니 담김수 * 6) + (주문 빈도수 * 10) + (조회수 // 3)
        demand_score = (sold_qty * 15) + (cart_qty * 6) + (order_freq * 10) + (view_cnt // 3)

        # 수요 상태 배지 태그 결정
        if total_stock <= 0:
            stock_badge = {"text": "품절", "class": "bg-danger text-white"}
        elif total_stock <= 5:
            stock_badge = {"text": f"품절임박 ({total_stock}개)", "class": "bg-warning text-dark"}
        else:
            stock_badge = {"text": f"여유 ({total_stock}개)", "class": "bg-success-subtle text-success border"}

        if demand_score >= 40 or sold_qty >= 2:
            demand_badge = {"text": "🔥 수요 폭발", "class": "bg-danger text-white"}
        elif demand_score >= 20 or cart_qty > 0:
            demand_badge = {"text": "⚡ 인기 급상승", "class": "bg-warning text-dark"}
        else:
            demand_badge = {"text": "✨ 일반 수요", "class": "bg-light text-secondary border"}

        popular_products.append({
            "id": pid,
            "name": prod.get("name"),
            "image_url": img_url,
            "category": prod.get("slug") or "액세서리",
            "price": int(prod.get("sale_price") or prod.get("original_price") or 0),
            "original_price": int(prod.get("original_price") or 0),
            "sold_qty": sold_qty,
            "revenue": revenue,
            "revenue_formatted": f"{int(revenue):,}원",
            "cart_qty": cart_qty,
            "view_cnt": view_cnt,
            "total_stock": total_stock,
            "demand_score": demand_score,
            "stock_badge": stock_badge,
            "demand_badge": demand_badge,
            "options_count": len(options),
        })

    # 수요 점수(Demand Score) 내림차순, 그 다음 판매량 내림차순으로 정렬
    popular_products.sort(key=lambda p: (p["demand_score"], p["sold_qty"], p["revenue"]), reverse=True)

    # 1위부터 순위 랭킹(Rank) 부여
    for idx, item in enumerate(popular_products):
        item["rank"] = idx + 1

    # =========================================================================
    # C. 회원 정보 (Member Information) 가공
    # =========================================================================
    members_data = []
    for prof in profiles:
        created_str = prof.get("created_at") or ""
        if created_str:
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                formatted_created = dt.strftime("%Y-%m-%d")
            except Exception:
                formatted_created = created_str[:10]
        else:
            formatted_created = "-"

        # 회원 총 구매액 및 주문 수 계산
        user_id = prof.get("id")
        user_orders = [o for o in orders if o.get("user_id") == user_id]
        calc_order_count = len(user_orders)
        calc_total_spent = sum(float(o.get("final_amount") or 0) for o in user_orders if o.get("status") in ["paid", "preparing", "shipped", "delivered"])

        members_data.append({
            "id": user_id,
            "name": prof.get("full_name") or "이름 미등록",
            "email": prof.get("email") or "-",
            "phone": prof.get("phone") or "미등록",
            "grade": prof.get("grade") or "BRONZE",
            "role": prof.get("role") or "customer",
            "avatar_url": prof.get("avatar_url") or "/static/images/strawberry_icon.svg",
            "order_count": max(calc_order_count, int(prof.get("order_count") or 0)),
            "total_spent": max(calc_total_spent, float(prof.get("total_spent") or 0)),
            "total_spent_formatted": f"{int(max(calc_total_spent, float(prof.get('total_spent') or 0))):,}원",
            "created_at": formatted_created,
        })

    # =========================================================================
    # D. 주문자 정보 및 주문 목록 (Orderers & Orders Information) 가공
    # =========================================================================
    orders_data = []
    for ord_row in orders:
        created_str = ord_row.get("created_at") or ""
        if created_str:
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_date = created_str[:16].replace("T", " ")
        else:
            formatted_date = "-"

        # 주문자(회원) 프로필 정보 추출
        profile_rel = ord_row.get("profiles") or {}
        if isinstance(profile_rel, list) and len(profile_rel) > 0:
            profile_rel = profile_rel[0]

        buyer_name = profile_rel.get("full_name") or ord_row.get("recipient_name") or "주문자"
        buyer_email = profile_rel.get("email") or "-"
        buyer_grade = profile_rel.get("grade") or "BRONZE"

        # 주문 상품 항목들
        raw_items = ord_row.get("order_items") or []
        items_summary_parts = []
        for it in raw_items:
            items_summary_parts.append(f"{it.get('product_name')} ({it.get('option_description') or '기본'}) x {it.get('quantity')}개")
        items_summary = ", ".join(items_summary_parts) if items_summary_parts else "주문 상품"

        status_kor = {
            "pending": "결제대기",
            "paid": "결제완료",
            "preparing": "배송준비중",
            "shipped": "배송중",
            "delivered": "배송완료",
            "cancelled": "주문취소",
        }

        status_class = {
            "pending": "bg-secondary",
            "paid": "bg-success",
            "preparing": "bg-info text-dark",
            "shipped": "bg-primary",
            "delivered": "bg-dark",
            "cancelled": "bg-danger",
        }

        cur_status = ord_row.get("status") or "pending"

        orders_data.append({
            "id": ord_row.get("id"),
            "order_number": ord_row.get("order_number"),
            "date": formatted_date,
            "buyer_name": buyer_name,
            "buyer_email": buyer_email,
            "buyer_grade": buyer_grade,
            "recipient_name": ord_row.get("recipient_name") or buyer_name,
            "recipient_phone": ord_row.get("recipient_phone") or "-",
            "full_address": f"[{ord_row.get('postal_code') or '06236'}] {ord_row.get('shipping_address') or ''} {ord_row.get('shipping_detail_address') or ''}".strip(),
            "shipping_memo": ord_row.get("shipping_memo") or "",
            "final_amount": int(ord_row.get("final_amount") or 0),
            "final_amount_formatted": f"{int(ord_row.get('final_amount') or 0):,}원",
            "payment_method": "카카오페이" if ord_row.get("payment_method") == "kakaopay" else "신용카드",
            "status": cur_status,
            "status_label": status_kor.get(cur_status, cur_status),
            "status_class": status_class.get(cur_status, "bg-secondary"),
            "items_count": len(raw_items),
            "items_summary": items_summary,
            "items": raw_items,
        })

    # KPI 딕셔너리
    kpi_stats = {
        "total_revenue": f"{int(total_revenue):,}원",
        "total_orders": f"{total_orders_count}건",
        "total_members": f"{total_members_count}명",
        "low_stock_count": f"{low_stock_count}개 품목",
    }

    # 일자별 매출 및 주문 통계 계산 (최근 7일, 14일, 30일)
    analytics_data = {
        7: compute_daily_analytics(orders, 7),
        14: compute_daily_analytics(orders, 14),
        30: compute_daily_analytics(orders, 30),
    }

    return render_template(
        "admin/dashboard.html",
        kpi=kpi_stats,
        popular_products=popular_products,
        members=members_data,
        orders=orders_data,
        analytics=analytics_data,
    )


@admin_bp.route("/api/analytics/daily")
@admin_required
def api_daily_analytics():
    """
    일자별 매출 및 주문 추이 데이터 비동기 조회 API (GET /admin/api/analytics/daily?days=7)
    지원 기간: 7일, 14일, 30일
    """
    try:
        days = int(request.args.get("days", 7))
        if days not in [7, 14, 30]:
            days = 7
    except (ValueError, TypeError):
        days = 7

    supabase = get_supabase_admin_client() or get_supabase_client()
    orders = []
    if supabase:
        try:
            res = supabase.table("orders").select("id, status, final_amount, created_at").execute()
            orders = res.data or []
        except Exception as e:
            print(f"[오류] 일자별 매출 통계 조회 실패: {e}")

    result = compute_daily_analytics(orders, days)
    return jsonify({"success": True, **result})


@admin_bp.route("/orders/<order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    """
    주문 및 배송 상태 변경 처리 (POST /admin/orders/<order_id>/status)
    지원 상태: paid, preparing, shipped, delivered, cancelled
    """
    new_status = request.form.get("status", "").strip()
    valid_statuses = ["pending", "paid", "preparing", "shipped", "delivered", "cancelled"]

    if new_status not in valid_statuses:
        flash("유효하지 않은 주문 상태입니다.", "danger")
        return redirect(url_for("admin.dashboard") + "#orders")

    supabase = get_supabase_admin_client() or get_supabase_client()
    if supabase:
        try:
            update_data = {
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if new_status == "cancelled":
                update_data["cancelled_at"] = datetime.utcnow().isoformat()

            res = supabase.table("orders").update(update_data).eq("id", order_id).execute()
            if res.data and len(res.data) > 0:
                flash(f"주문 상태가 '{new_status}'(으)로 성공적으로 변경되었습니다. 🍓", "success")
            else:
                flash("해당 주문을 찾을 수 없습니다.", "warning")
        except Exception as e:
            print(f"[오류] 주문 상태 변경 실패: {e}")
            flash(f"주문 상태 변경 중 오류가 발생했습니다: {e}", "danger")

    return redirect(url_for("admin.dashboard") + "#orders")


@admin_bp.route("/members/<user_id>/grade", methods=["POST"])
@admin_required
def update_member_grade(user_id):
    """
    회원 등급 변경 처리 (POST /admin/members/<user_id>/grade)
    지원 등급: BRONZE, SILVER, GOLD, VIP
    """
    new_grade = request.form.get("grade", "").strip().upper()
    valid_grades = ["BRONZE", "SILVER", "GOLD", "VIP"]

    if new_grade not in valid_grades:
        flash("유효하지 않은 회원 등급입니다.", "danger")
        return redirect(url_for("admin.dashboard") + "#members")

    supabase = get_supabase_admin_client() or get_supabase_client()
    if supabase:
        try:
            res = (
                supabase.table("profiles")
                .update({"grade": new_grade, "updated_at": datetime.utcnow().isoformat()})
                .eq("id", user_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                flash(f"회원 등급이 '{new_grade}'(으)로 업데이트되었습니다.", "success")
            else:
                flash("해당 회원을 찾을 수 없습니다.", "warning")
        except Exception as e:
            print(f"[오류] 회원 등급 변경 실패: {e}")
            flash("회원 등급 변경 중 오류가 발생했습니다.", "danger")

    return redirect(url_for("admin.dashboard") + "#members")


@admin_bp.route("/members/<user_id>/role", methods=["POST"])
@admin_required
def update_member_role(user_id):
    """
    회원 관리자 권한/일반회원 권한 토글 처리 (POST /admin/members/<user_id>/role)
    지원 권한: customer, admin
    """
    new_role = request.form.get("role", "").strip().lower()
    if new_role not in ["customer", "admin"]:
        flash("유효하지 않은 권한입니다.", "danger")
        return redirect(url_for("admin.dashboard") + "#members")

    supabase = get_supabase_admin_client() or get_supabase_client()
    if supabase:
        try:
            res = (
                supabase.table("profiles")
                .update({"role": new_role, "updated_at": datetime.utcnow().isoformat()})
                .eq("id", user_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                flash(f"회원 권한이 '{new_role}'(으)로 변경되었습니다.", "success")
            else:
                flash("해당 회원을 찾을 수 없습니다.", "warning")
        except Exception as e:
            print(f"[오류] 회원 권한 변경 실패: {e}")
            flash("회원 권한 변경 중 오류가 발생했습니다.", "danger")

    return redirect(url_for("admin.dashboard") + "#members")


@admin_bp.route("/api/orders/<order_id>")
@admin_required
def api_order_detail(order_id):
    """
    주문 상세 팝업용 JSON API (GET /admin/api/orders/<order_id>)
    """
    supabase = get_supabase_admin_client() or get_supabase_client()
    if not supabase:
        return jsonify({"success": False, "message": "DB 연결 오류"}), 500

    try:
        ord_res = (
            supabase.table("orders")
            .select("*, profiles(full_name, email, phone), order_items(*)")
            .eq("id", order_id)
            .limit(1)
            .execute()
        )
        if ord_res.data and len(ord_res.data) > 0:
            return jsonify({"success": True, "order": ord_res.data[0]})
        return jsonify({"success": False, "message": "주문을 찾을 수 없습니다."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def fetch_inventory_data():
    """
    재고 관리 페이지용 통합 데이터 조회 및 가공 함수
    - 모든 상품과 해당 옵션의 현재 재고, 누적 판매량, 상태 배지 집계
    - 재고 관리 KPI 요약 통계 산출
    """
    supabase = get_supabase_admin_client() or get_supabase_client()
    inventory_items = []
    kpi = {
        "total_skus": 0,
        "total_units": 0,
        "in_stock_count": 0,
        "low_stock_count": 0,
        "out_of_stock_count": 0,
        "total_sold_count": 0,
    }

    if not supabase:
        return inventory_items, kpi

    try:
        # 상품 및 옵션, 이미지 조회
        prods_res = (
            supabase.table("products")
            .select("id, name, slug, original_price, sale_price, stock_quantity, status, product_images(image_url), product_options(id, option_name, option_value, color, size, stock, stock_quantity, is_available)")
            .order("id")
            .execute()
        )
        products = prods_res.data or []

        # 누적 판매량 집계 (order_items)
        items_res = supabase.table("order_items").select("product_id, option_id, quantity").execute()
        sold_map = {}
        for it in items_res.data or []:
            oid = it.get("option_id")
            if oid:
                sold_map[oid] = sold_map.get(oid, 0) + int(it.get("quantity") or 1)
                kpi["total_sold_count"] += int(it.get("quantity") or 1)

        for p in products:
            p_id = p["id"]
            p_name = p["name"]
            p_price = int(p.get("sale_price") or p.get("original_price") or 0)
            p_status = p.get("status", "active")

            images = p.get("product_images") or []
            p_img = images[0].get("image_url") if images else "/static/images/real_pink_rabbit.png"

            options = p.get("product_options") or []

            # 옵션이 없는 단품 상품인 경우 가상 기본 옵션 1개 생성
            if not options:
                stk = int(p.get("stock_quantity") or 0)
                options = [{
                    "id": f"p_{p_id}",
                    "option_name": "기본",
                    "option_value": "단일 상품",
                    "color": None,
                    "size": None,
                    "stock": stk,
                    "stock_quantity": stk,
                    "is_available": stk > 0
                }]

            for opt in options:
                opt_id = opt.get("id")
                raw_stock = opt.get("stock")
                if raw_stock is None:
                    raw_stock = opt.get("stock_quantity", 0)
                stock_qty = int(raw_stock or 0)

                # 옵션 텍스트 생성
                color = (opt.get("color") or "").strip()
                size = (opt.get("size") or "").strip()
                opt_name = (opt.get("option_name") or "").strip()
                opt_val = (opt.get("option_value") or "").strip()

                opt_parts = []
                if color:
                    opt_parts.append(color)
                if size:
                    opt_parts.append(size)
                if not opt_parts and opt_name and opt_val:
                    opt_parts.append(f"{opt_name}: {opt_val}")
                display_option = " / ".join(opt_parts) if opt_parts else "기본 옵션"

                sold_qty = sold_map.get(opt_id, 0)

                # 상태 판별: 정상(>5), 품절임박(1~5), 품절(<=0)
                if stock_qty <= 0:
                    status_type = "out_of_stock"
                    status_label = "품절"
                    badge_class = "bg-danger text-white"
                    kpi["out_of_stock_count"] += 1
                elif stock_qty <= 5:
                    status_type = "low_stock"
                    status_label = f"품절임박 ({stock_qty}개)"
                    badge_class = "bg-warning text-dark"
                    kpi["low_stock_count"] += 1
                else:
                    status_type = "in_stock"
                    status_label = f"정상 재고 ({stock_qty}개)"
                    badge_class = "bg-success-subtle text-success border border-success-subtle"
                    kpi["in_stock_count"] += 1

                kpi["total_skus"] += 1
                kpi["total_units"] += stock_qty

                inventory_items.append({
                    "product_id": p_id,
                    "product_name": p_name,
                    "product_price": p_price,
                    "product_price_formatted": f"{p_price:,}원",
                    "product_status": p_status,
                    "image_url": p_img,
                    "option_id": opt_id,
                    "display_option": display_option,
                    "color": color,
                    "size": size,
                    "stock": stock_qty,
                    "sold_qty": sold_qty,
                    "status_type": status_type,
                    "status_label": status_label,
                    "badge_class": badge_class,
                    "is_real_option": isinstance(opt_id, int),
                })

    except Exception as e:
        print(f"[오류] 재고 목록 조회 실패: {e}")

    return inventory_items, kpi


@admin_bp.route("/inventory")
@admin_required
def inventory():
    """
    재고 관리 전용 페이지 (GET /admin/inventory)
    - 실시간 전체 상품 및 옵션별 재고 현황 조회
    - 빠른 입고/차감, 수량 직접 수정, 품절 처리
    """
    items, kpi = fetch_inventory_data()
    return render_template(
        "admin/inventory.html",
        items=items,
        kpi=kpi,
    )


@admin_bp.route("/inventory/options/<int:option_id>/stock", methods=["POST"])
@admin_required
def update_option_stock(option_id):
    """
    상품 옵션 재고 수량 수정 처리 (POST /admin/inventory/options/<option_id>/stock)
    - 절대 수량 설정(stock) 또는 상대 증감(delta: +10, -5 등) 지원
    - product_options 테이블 및 부모 products 테이블의 총 재고를 실시간 동기화
    """
    data = request.get_json(silent=True) or request.form
    supabase = get_supabase_admin_client() or get_supabase_client()

    if not supabase:
        if request.is_json:
            return jsonify({"success": False, "message": "데이터베이스 연결 오류"}), 500
        flash("데이터베이스 연결에 실패했습니다.", "danger")
        return redirect(url_for("admin.inventory"))

    try:
        # 기존 옵션 데이터 조회
        opt_res = (
            supabase.table("product_options")
            .select("id, product_id, stock, stock_quantity")
            .eq("id", option_id)
            .limit(1)
            .execute()
        )
        if not opt_res.data or len(opt_res.data) == 0:
            if request.is_json:
                return jsonify({"success": False, "message": "해당 옵션을 찾을 수 없습니다."}), 404
            flash("해당 상품 옵션을 찾을 수 없습니다.", "warning")
            return redirect(url_for("admin.inventory"))

        cur_opt = opt_res.data[0]
        product_id = cur_opt.get("product_id")
        current_stock = int(cur_opt.get("stock") if cur_opt.get("stock") is not None else cur_opt.get("stock_quantity") or 0)

        # 새 재고 수량 산출
        if "stock" in data and str(data["stock"]).strip() != "":
            new_stock = max(0, int(data["stock"]))
        elif "delta" in data:
            delta = int(data["delta"])
            new_stock = max(0, current_stock + delta)
        else:
            new_stock = current_stock

        is_avail = new_stock > 0

        # 1. product_options 테이블 갱신
        supabase.table("product_options").update({
            "stock": new_stock,
            "stock_quantity": new_stock,
            "is_available": is_avail,
        }).eq("id", option_id).execute()

        # 2. 부모 products 테이블 총 재고 합계 재계산 및 동기화
        all_opts = (
            supabase.table("product_options")
            .select("stock, stock_quantity")
            .eq("product_id", product_id)
            .execute()
        )
        total_p_stock = sum(int(o.get("stock") if o.get("stock") is not None else o.get("stock_quantity") or 0) for o in (all_opts.data or []))

        p_status = "active" if total_p_stock > 0 else "sold_out"
        supabase.table("products").update({
            "stock_quantity": total_p_stock,
            "status": p_status,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", product_id).execute()

        msg = f"옵션(#{option_id}) 재고가 {new_stock}개로 성공적으로 업데이트되었습니다. (상품 총재고: {total_p_stock}개)"

        if request.is_json:
            return jsonify({
                "success": True,
                "message": msg,
                "option_id": option_id,
                "new_stock": new_stock,
                "total_product_stock": total_p_stock,
                "is_available": is_avail,
            }), 200

        flash(msg, "success")

    except Exception as e:
        print(f"[오류] 재고 수정 실패: {e}")
        if request.is_json:
            return jsonify({"success": False, "message": f"재고 수정 중 오류가 발생했습니다: {e}"}), 500
        flash("재고 수정 중 오류가 발생했습니다.", "danger")

    return redirect(request.referrer or url_for("admin.inventory"))


@admin_bp.route("/inventory/options/<int:option_id>/toggle", methods=["POST"])
@admin_required
def toggle_option_stock(option_id):
    """
    원클릭 품절 처리 / 정상 재고 입고 토글 처리
    - 현재 재고 > 0 이면 -> 0개(품절)로 변경
    - 현재 재고 <= 0 이면 -> 20개(기본 입고)로 변경
    """
    supabase = get_supabase_admin_client() or get_supabase_client()
    if not supabase:
        return jsonify({"success": False, "message": "DB 연결 오류"}), 500

    try:
        opt_res = supabase.table("product_options").select("id, product_id, stock, stock_quantity").eq("id", option_id).limit(1).execute()
        if not opt_res.data:
            return jsonify({"success": False, "message": "옵션 없음"}), 404

        cur_stk = int(opt_res.data[0].get("stock") if opt_res.data[0].get("stock") is not None else opt_res.data[0].get("stock_quantity") or 0)
        target_stock = 0 if cur_stk > 0 else 20
        product_id = opt_res.data[0]["product_id"]

        supabase.table("product_options").update({
            "stock": target_stock,
            "stock_quantity": target_stock,
            "is_available": target_stock > 0,
        }).eq("id", option_id).execute()

        # 부모 상품 재고 동기화
        all_opts = supabase.table("product_options").select("stock").eq("product_id", product_id).execute()
        total_p_stock = sum(int(o.get("stock") or 0) for o in (all_opts.data or []))
        supabase.table("products").update({
            "stock_quantity": total_p_stock,
            "status": "active" if total_p_stock > 0 else "sold_out"
        }).eq("id", product_id).execute()

        msg = f"옵션 재고가 {'품절(0개)' if target_stock == 0 else f'입고({target_stock}개)'}로 전환되었습니다."
        if request.is_json:
            return jsonify({
                "success": True,
                "message": msg,
                "new_stock": target_stock,
                "total_product_stock": total_p_stock,
            })
        flash(msg, "success")

    except Exception as e:
        print(f"[오류] 품절 토글 오류: {e}")
        if request.is_json:
            return jsonify({"success": False, "message": str(e)}), 500
        flash("재고 상태 전환 중 오류가 발생했습니다.", "danger")

    return redirect(request.referrer or url_for("admin.inventory"))


@admin_bp.route("/inventory/products/<int:product_id>/status", methods=["POST"])
@admin_required
def update_product_status(product_id):
    """
    상품 판매 상태 변경 (active: 판매중, sold_out: 품절, hidden: 숨김)
    """
    new_status = request.form.get("status", "").strip().lower()
    valid_statuses = ["active", "sold_out", "hidden"]

    if new_status not in valid_statuses:
        flash("유효하지 않은 상품 상태입니다.", "danger")
        return redirect(url_for("admin.inventory"))

    supabase = get_supabase_admin_client() or get_supabase_client()
    if supabase:
        try:
            supabase.table("products").update({
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", product_id).execute()
            flash(f"상품(#{product_id})의 판매 상태가 '{new_status}'(으)로 변경되었습니다.", "success")
        except Exception as e:
            print(f"[오류] 상품 상태 변경 실패: {e}")
            flash("상품 상태 변경 중 오류가 발생했습니다.", "danger")

    return redirect(request.referrer or url_for("admin.inventory"))
