-- ==============================================================================
-- VIBE-FASHION 초기 데이터(Seed) SQL
-- ==============================================================================

-- 1. 카테고리 7개 등록 (상위 카테고리)
INSERT INTO public.categories (name, slug, description, sort_order, is_active)
VALUES 
    ('상의', 'top', '티셔츠, 셔츠, 니트, 맨투맨 등 상의 카테고리', 1, true),
    ('하의', 'bottom', '청바지, 슬랙스, 팬츠, 스커트 등 하의 카테고리', 2, true),
    ('아우터', 'outer', '자켓, 코트, 패딩, 가디건 등 아우터 카테고리', 3, true),
    ('원피스/세트', 'dress', '원피스, 투피스, 셋업 등', 4, true),
    ('액세서리', 'acc', '주얼리, 모자, 벨트, 양말 등 액세서리', 5, true),
    ('가방', 'bag', '숄더백, 토트백, 백팩, 크로스백 등', 6, true),
    ('신발', 'shoes', '스니커즈, 로퍼, 부츠, 샌들 등', 7, true)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    sort_order = EXCLUDED.sort_order,
    is_active = EXCLUDED.is_active;

-- ==============================================================================
-- 2. 샘플 상품 6개 등록 (CHIMUTAN & MONCHHICHI 공식 컬렉션)
-- ==============================================================================

INSERT INTO public.products (category_id, name, slug, summary, description, original_price, sale_price, stock_quantity, status, is_featured, view_count)
VALUES 
    (
        (SELECT id FROM public.categories WHERE slug = 'acc'),
        '[치무탄 정품] 핑크 토끼 페이스 인형 파우치 키링',
        'chimutan-pink-rabbit-keyring',
        '보송보송 핑크 토끼 귀와 딸기코가 사랑스러운 치무탄 오리지널 동전지갑 겸 인형 백참 키링입니다.',
        '<p>보송보송 핑크 토끼 귀와 딸기코가 사랑스러운 치무탄 오리지널 동전지갑 겸 인형 백참 키링입니다.</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다.</p>',
        32000,
        26000,
        50,
        'active',
        true,
        150
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'acc'),
        '[치무탄 스트로베리] 레드 딸기 토끼 페이스 파우치',
        'chimutan-strawberry-rabbit-pouch',
        '상큼한 레드 컬러에 초록색 딸기 꼭지와 씨앗 디테일이 돋보이는 한정판 스트로베리 토끼 파우치입니다.',
        '<p>상큼한 레드 컬러에 초록색 딸기 꼭지와 씨앗 디테일이 돋보이는 한정판 스트로베리 토끼 파우치입니다.</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다.</p>',
        34000,
        27000,
        45,
        'active',
        true,
        120
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'acc'),
        '[몬치치 클래식] 오리지널 레드 레더 체인 지갑',
        'monchhichi-red-leather-wallet',
        '빈티지한 레드 가죽 질감에 귀여운 몬치치 오리지널 캐릭터와 볼체인 키링이 달린 지퍼형 동전 지갑입니다.',
        '<p>빈티지한 레드 가죽 질감에 귀여운 몬치치 오리지널 캐릭터와 볼체인 키링이 달린 지퍼형 동전 지갑입니다.</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다.</p>',
        28000,
        22000,
        40,
        'active',
        true,
        110
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'acc'),
        '[몬치치 백참] 아이보리 베어 토트백 키링',
        'monchhichi-ivory-bear-keyring',
        '토트백이나 에코백 손잡이에 바로 걸 수 있는 실버 체인이 달린 보송보송 아이보리 베어 키링입니다.',
        '<p>토트백이나 에코백 손잡이에 바로 걸 수 있는 실버 체인이 달린 보송보송 아이보리 베어 키링입니다.</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다.</p>',
        28000,
        23000,
        60,
        'active',
        true,
        95
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'acc'),
        '[치무탄 홈웨어] 포근한 핑크 체크 딸기 수면양말',
        'chimutan-pink-sleep-socks',
        '보들보들한 핑크 깅엄체크 극세사 퍼에 발목의 입체 딸기 니팅 자수와 화이트 보아퍼 밴딩이 더해진 보온 수면양말입니다.',
        '<p>보들보들한 핑크 깅엄체크 극세사 퍼에 발목의 입체 딸기 니팅 자수와 화이트 보아퍼 밴딩이 더해진 보온 수면양말입니다.</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다.</p>',
        18000,
        14000,
        75,
        'active',
        false,
        85
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'acc'),
        '[스페셜 화보] 몬치치 &amp; 치무탄 3종 룩북 에디션',
        'monchhichi-chimutan-special-set',
        '스트로베리 토끼, 핑크 치무탄, 가방 베어 키링 3종이 담긴 실물 촬영 공식 룩북 세트입니다.',
        '<p>스트로베리 토끼, 핑크 치무탄, 가방 베어 키링 3종이 담긴 실물 촬영 공식 룩북 세트입니다.</p><p>몬치치 &amp; 치무탄 공식 콜라보레이션 정품 제품입니다. 한정판입니다.</p>',
        95000,
        75000,
        20,
        'active',
        true,
        200
    )
ON CONFLICT (slug) DO UPDATE SET
    category_id = EXCLUDED.category_id,
    name = EXCLUDED.name,
    summary = EXCLUDED.summary,
    description = EXCLUDED.description,
    original_price = EXCLUDED.original_price,
    sale_price = EXCLUDED.sale_price,
    stock_quantity = EXCLUDED.stock_quantity,
    status = EXCLUDED.status,
    is_featured = EXCLUDED.is_featured;

-- ==============================================================================
-- 3. 상품 옵션 등록 (CHIMUTAN & MONCHHICHI 상품의 색상/사이즈 옵션)
-- ==============================================================================

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
INSERT INTO public.product_options (product_id, option_name, option_value, size, stock_quantity, is_available)
SELECT 
    p.id,
    '사이즈',
    opt_value,
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
INSERT INTO public.product_options (product_id, option_name, option_value, stock_quantity, is_available)
SELECT 
    p.id,
    '기본',
    '1 Set',
    20,
    true
FROM public.products p
WHERE p.slug = 'monchhichi-chimutan-special-set';

-- ==============================================================================
-- 4. 상품 이미지 등록 (로컬 정적 이미지 사용)
-- ==============================================================================

-- 중복 삽입 방지를 위해 기존 이미지 정리 후 삽입
DELETE FROM public.product_images 
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

INSERT INTO public.product_images (product_id, image_url, alt_text, sort_order, is_thumbnail)
VALUES
    -- 1) 핑크 토끼 키링
    (
        (SELECT id FROM public.products WHERE slug = 'chimutan-pink-rabbit-keyring'),
        '/static/images/real_pink_rabbit.png',
        '핑크 토끼 페이스 인형 파우치 키링',
        1,
        true
    ),

    -- 2) 딸기 토끼 파우치
    (
        (SELECT id FROM public.products WHERE slug = 'chimutan-strawberry-rabbit-pouch'),
        '/static/images/real_strawberry_rabbit.png',
        '레드 딸기 토끼 페이스 파우치',
        1,
        true
    ),

    -- 3) 레드 레더 지갑
    (
        (SELECT id FROM public.products WHERE slug = 'monchhichi-red-leather-wallet'),
        '/static/images/real_monchhichi_red_wallet.png',
        '몬치치 클래식 오리지널 레드 레더 체인 지갑',
        1,
        true
    ),

    -- 4) 아이보리 베어 키링
    (
        (SELECT id FROM public.products WHERE slug = 'monchhichi-ivory-bear-keyring'),
        '/static/images/real_bag_bear_keyring.png',
        '몬치치 백참 아이보리 베어 토트백 키링',
        1,
        true
    ),

    -- 5) 수면양말
    (
        (SELECT id FROM public.products WHERE slug = 'chimutan-pink-sleep-socks'),
        '/static/images/real_strawberry_sleep_socks.png',
        '포근한 핑크 체크 딸기 수면양말',
        1,
        true
    ),

    -- 6) 3종 세트
    (
        (SELECT id FROM public.products WHERE slug = 'monchhichi-chimutan-special-set'),
        '/static/images/real_monchhichi_group.png',
        '몬치치 & 치무탄 3종 룩북 에디션',
        1,
        true
    );
