-- ==============================================================================
-- Day 5 실습 Seed SQL: products 테이블의 모든 상품에 대한 색상 x 사이즈 옵션 생성
-- ==============================================================================
-- - products 테이블의 실제 id를 동적으로 조회하여 연동
-- - 각 상품당 색상 3종 (Black, White, Beige) x 사이즈 3종 (S, M, L) = 9개 조합 생성
-- - 재고(stock): 0(품절), 1(품절 임박), 10~30(충분) 다양하게 분포
-- - 재실행 시 중복 삽입 방지 (ON CONFLICT DO UPDATE 적용)
-- ==============================================================================

WITH option_matrix AS (
    -- 1. 색상(3종) x 사이즈(3종) 기본 조합 및 실습용 테스트 재고 패턴 정의
    SELECT * FROM (
        VALUES
            ('Black', 'S', 15),  -- 충분
            ('Black', 'M', 25),  -- 충분
            ('Black', 'L', 0),   -- 품절 시나리오 테스트용 (재고 0)
            ('White', 'S', 1),   -- 품절 임박 시나리오 테스트용 (재고 1)
            ('White', 'M', 20),  -- 충분
            ('White', 'L', 10),  -- 충분
            ('Beige', 'S', 0),   -- 품절 시나리오 테스트용 (재고 0)
            ('Beige', 'M', 1),   -- 품절 임박 시나리오 테스트용 (재고 1)
            ('Beige', 'L', 30)   -- 충분
    ) AS t(color, size, base_stock)
),
all_products_options AS (
    -- 2. 실제 DB의 products 전체 상품과 옵션 조합 결합
    -- 상품 id에 따라 재고를 약간씩 변형하여(0, 1, 10~30) 상품마다 다른 품절 상태 연출
    SELECT 
        p.id AS product_id,
        m.color,
        m.size,
        CASE 
            -- 특정 조합은 무조건 품절(0) 또는 품절임박(1) 유지
            WHEN m.base_stock = 0 THEN 0
            WHEN m.base_stock = 1 THEN 1
            -- 그 외는 상품 id 기반으로 10~30 사이의 충분한 재고 부여
            ELSE 10 + ((p.id * 3 + CASE m.size WHEN 'S' THEN 2 WHEN 'M' THEN 5 ELSE 8 END) % 21)
        END AS stock,
        m.color || ' / ' || m.size AS option_value,
        0 AS additional_price
    FROM public.products p
    CROSS JOIN option_matrix m
)
INSERT INTO public.product_options (
    product_id, 
    color, 
    size, 
    stock, 
    stock_quantity, 
    option_name, 
    option_value, 
    additional_price, 
    is_available
)
SELECT 
    product_id,
    color,
    size,
    stock,
    stock AS stock_quantity,    -- 기존 레거시 컬럼과의 호환성 유지
    '색상/사이즈' AS option_name,
    option_value,
    additional_price,
    (stock > 0) AS is_available -- 재고가 0이면 판매 불가(false) 처리
FROM all_products_options
ON CONFLICT (product_id, color, size) WHERE color IS NOT NULL AND size IS NOT NULL
DO UPDATE SET
    stock = EXCLUDED.stock,
    stock_quantity = EXCLUDED.stock_quantity,
    is_available = EXCLUDED.is_available;
