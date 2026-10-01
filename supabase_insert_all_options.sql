-- ================================================================
-- 모든 상품의 색상/사이즈 옵션 데이터 한 번에 삽입
-- Supabase SQL Editor에 복사해서 붙여넣고 Run 실행
-- ================================================================

-- Step 1: 기존 옵션 삭제 (중복 방지)
DELETE FROM public.product_options 
WHERE product_id IN (
    SELECT id FROM public.products 
    WHERE slug IN (
        'chimutan-pink-rabbit-keyring',
        'chimutan-strawberry-rabbit-pouch', 
        'monchhichi-red-leather-wallet',
        'monchhichi-ivory-bear-keyring',
        'chimutan-pink-sleep-socks',
        'monchhichi-chimutan-special-set'
    )
);

-- Step 2: Product 1 - 핑크 토끼 키링 (색상별 사이즈)
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT p.id, '색상/사이즈', CONCAT(opt_color, ' / Free'), opt_color, 'Free', 15, true
FROM public.products p
CROSS JOIN (VALUES ('Pink'), ('White'), ('Beige')) AS opt(opt_color)
WHERE p.slug = 'chimutan-pink-rabbit-keyring';

-- Step 3: Product 2 - 딸기 토끼 파우치 (색상별 사이즈)
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT p.id, '색상/사이즈', CONCAT(opt_color, ' / Free'), opt_color, 'Free', 15, true
FROM public.products p
CROSS JOIN (VALUES ('Red'), ('Pink'), ('White')) AS opt(opt_color)
WHERE p.slug = 'chimutan-strawberry-rabbit-pouch';

-- Step 4: Product 3 - 레드 레더 지갑 (색상별 사이즈)
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT p.id, '색상/사이즈', CONCAT(opt_color, ' / Free'), opt_color, 'Free', 13, true
FROM public.products p
CROSS JOIN (VALUES ('Red'), ('Black'), ('Brown')) AS opt(opt_color)
WHERE p.slug = 'monchhichi-red-leather-wallet';

-- Step 5: Product 4 - 아이보리 베어 키링 (색상별 사이즈) ⭐ Light Brown 포함
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT p.id, '색상/사이즈', CONCAT(opt_color, ' / Free'), opt_color, 'Free', 20, true
FROM public.products p
CROSS JOIN (VALUES ('Ivory'), ('Light Brown'), ('Gray')) AS opt(opt_color)
WHERE p.slug = 'monchhichi-ivory-bear-keyring';

-- Step 6: Product 5 - 수면양말 (사이즈만)
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT p.id, '사이즈', opt_value, NULL, opt_value, 25, true
FROM public.products p
CROSS JOIN (VALUES ('Free'), ('M'), ('L')) AS opt(opt_value)
WHERE p.slug = 'chimutan-pink-sleep-socks';

-- Step 7: Product 6 - 3종 세트 (옵션 없음)
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT p.id, '기본', '1 Set', NULL, NULL, 20, true
FROM public.products p
WHERE p.slug = 'monchhichi-chimutan-special-set';
