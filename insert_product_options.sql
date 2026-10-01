-- 중복 삽입 방지를 위해 기존 옵션 정리 후 삽입
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

-- 첫 번째 상품(핑크 토끼 키링) 옵션 - 색상별 사이즈
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT 
    p.id,
    '색상/사이즈',
    CONCAT(opt_color, ' / Free'),
    opt_color,
    'Free',
    15,
    true
FROM public.products p
CROSS JOIN (
    VALUES 
        ('Pink'),
        ('White'),
        ('Beige')
) AS opt(opt_color)
WHERE p.slug = 'chimutan-pink-rabbit-keyring';

-- 두 번째 상품(딸기 토끼 파우치) 옵션 - 색상별 사이즈
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT 
    p.id,
    '색상/사이즈',
    CONCAT(opt_color, ' / Free'),
    opt_color,
    'Free',
    15,
    true
FROM public.products p
CROSS JOIN (
    VALUES 
        ('Red'),
        ('Pink'),
        ('White')
) AS opt(opt_color)
WHERE p.slug = 'chimutan-strawberry-rabbit-pouch';

-- 세 번째 상품(레드 레더 지갑) 옵션 - 색상별 사이즈
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT 
    p.id,
    '색상/사이즈',
    CONCAT(opt_color, ' / Free'),
    opt_color,
    'Free',
    13,
    true
FROM public.products p
CROSS JOIN (
    VALUES 
        ('Red'),
        ('Black'),
        ('Brown')
) AS opt(opt_color)
WHERE p.slug = 'monchhichi-red-leather-wallet';

-- 네 번째 상품(아이보리 베어 키링) 옵션 - 색상별 사이즈
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT 
    p.id,
    '색상/사이즈',
    CONCAT(opt_color, ' / Free'),
    opt_color,
    'Free',
    20,
    true
FROM public.products p
CROSS JOIN (
    VALUES 
        ('Ivory'),
        ('Light Brown'),
        ('Gray')
) AS opt(opt_color)
WHERE p.slug = 'monchhichi-ivory-bear-keyring';

-- 다섯 번째 상품(수면양말) 옵션 - 사이즈
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT 
    p.id,
    '사이즈',
    opt_value,
    NULL,
    opt_value,
    25,
    true
FROM public.products p
CROSS JOIN (
    VALUES 
        ('Free'),
        ('M'),
        ('L')
) AS opt(opt_value)
WHERE p.slug = 'chimutan-pink-sleep-socks';

-- 여섯 번째 상품(3종 세트) 옵션 - 기본
INSERT INTO public.product_options (product_id, option_name, option_value, color, size, stock_quantity, is_available)
SELECT 
    p.id,
    '기본',
    '1 Set',
    NULL,
    NULL,
    20,
    true
FROM public.products p
WHERE p.slug = 'monchhichi-chimutan-special-set';
