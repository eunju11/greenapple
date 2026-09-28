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
-- 2. 샘플 상품 4개 등록
-- 주의: 스키마 제약조건(sale_price <= original_price)을 만족하도록
-- '베이직 크롭 티셔츠'는 원가 29,900원, 할인가 19,900원으로 정상 배치합니다.
-- ==============================================================================

INSERT INTO public.products (category_id, name, slug, summary, description, original_price, sale_price, stock_quantity, status, is_featured, view_count)
VALUES 
    (
        (SELECT id FROM public.categories WHERE slug = 'top'),
        '베이직 크롭 티셔츠',
        'basic-crop-tshirt',
        '데일리로 입기 좋은 탄탄한 코튼 100% 베이직 크롭 티셔츠',
        '<p>어디에나 매치하기 쉬운 기본 크롭 티셔츠입니다. 탄탄한 20수 코튼 원단으로 늘어짐 없이 오래 착용할 수 있습니다.</p>',
        29900,
        19900,
        180,
        'active',
        true,
        120
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'bottom'),
        '와이드 데님 팬츠',
        'wide-denim-pants',
        '자연스러운 워싱과 트렌디한 와이드 실루엣의 데님 팬츠',
        '<p>체형 커버에 탁월한 하이웨이스트 와이드 핏 데님입니다. 사계절 내내 착용 가능한 두께감입니다.</p>',
        39900,
        NULL,
        80,
        'active',
        true,
        95
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'outer'),
        '오버핏 코튼 자켓',
        'overfit-cotton-jacket',
        '가볍게 걸치기 좋은 캐주얼 오버핏 워싱 코튼 자켓',
        '<p>간절기에 활용하기 좋은 트렌디한 무드의 오버사이즈 코튼 자켓입니다. 탄탄한 마감 처리가 돋보입니다.</p>',
        59900,
        NULL,
        45,
        'active',
        false,
        64
    ),
    (
        (SELECT id FROM public.categories WHERE slug = 'dress'),
        '플로럴 미디 원피스',
        'floral-midi-dress',
        '화사한 잔꽃 패턴과 우아한 실루엣의 미디 롱 원피스',
        '<p>여성스러운 무드를 연출해주는 브이넥 플로럴 패턴 원피스입니다. 허리 스트랩으로 핏 조절이 가능합니다.</p>',
        45900,
        NULL,
        30,
        'active',
        true,
        88
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
-- 3. 상품 옵션 등록
-- 첫 번째 상품(베이직 크롭 티셔츠) 옵션 9개 (블랙/화이트/베이지 × S/M/L)
-- ==============================================================================

-- 중복 삽입 방지를 위해 기존 옵션 정리 후 삽입
DELETE FROM public.product_options 
WHERE product_id = (SELECT id FROM public.products WHERE slug = 'basic-crop-tshirt');

INSERT INTO public.product_options (product_id, option_name, option_value, additional_price, stock_quantity, is_available)
SELECT 
    p.id,
    opt.option_name,
    opt.option_value,
    0,
    20,
    true
FROM public.products p
CROSS JOIN (
    VALUES 
        ('컬러/사이즈', '블랙 / S'),
        ('컬러/사이즈', '블랙 / M'),
        ('컬러/사이즈', '블랙 / L'),
        ('컬러/사이즈', '화이트 / S'),
        ('컬러/사이즈', '화이트 / M'),
        ('컬러/사이즈', '화이트 / L'),
        ('컬러/사이즈', '베이지 / S'),
        ('컬러/사이즈', '베이지 / M'),
        ('컬러/사이즈', '베이지 / L')
) AS opt(option_name, option_value)
WHERE p.slug = 'basic-crop-tshirt';

-- ==============================================================================
-- 4. 상품 이미지 등록 (picsum.photos 무료 이미지 사용)
-- ==============================================================================

-- 중복 삽입 방지를 위해 샘플 상품들의 기존 이미지 정리 후 삽입
DELETE FROM public.product_images 
WHERE product_id IN (
    SELECT id FROM public.products 
    WHERE slug IN ('basic-crop-tshirt', 'wide-denim-pants', 'overfit-cotton-jacket', 'floral-midi-dress')
);

INSERT INTO public.product_images (product_id, image_url, alt_text, sort_order, is_thumbnail)
VALUES
    -- 1) 베이직 크롭 티셔츠
    (
        (SELECT id FROM public.products WHERE slug = 'basic-crop-tshirt'),
        'https://picsum.photos/seed/vibe_crop_top_thumb/600/800',
        '베이직 크롭 티셔츠 대표 썸네일',
        1,
        true
    ),
    (
        (SELECT id FROM public.products WHERE slug = 'basic-crop-tshirt'),
        'https://picsum.photos/seed/vibe_crop_top_detail1/600/800',
        '베이직 크롭 티셔츠 착용컷',
        2,
        false
    ),

    -- 2) 와이드 데님 팬츠
    (
        (SELECT id FROM public.products WHERE slug = 'wide-denim-pants'),
        'https://picsum.photos/seed/vibe_denim_pants_thumb/600/800',
        '와이드 데님 팬츠 대표 썸네일',
        1,
        true
    ),
    (
        (SELECT id FROM public.products WHERE slug = 'wide-denim-pants'),
        'https://picsum.photos/seed/vibe_denim_pants_detail1/600/800',
        '와이드 데님 팬츠 상세컷',
        2,
        false
    ),

    -- 3) 오버핏 코튼 자켓
    (
        (SELECT id FROM public.products WHERE slug = 'overfit-cotton-jacket'),
        'https://picsum.photos/seed/vibe_jacket_thumb/600/800',
        '오버핏 코튼 자켓 대표 썸네일',
        1,
        true
    ),
    (
        (SELECT id FROM public.products WHERE slug = 'overfit-cotton-jacket'),
        'https://picsum.photos/seed/vibe_jacket_detail1/600/800',
        '오버핏 코튼 자켓 디테일컷',
        2,
        false
    ),

    -- 4) 플로럴 미디 원피스
    (
        (SELECT id FROM public.products WHERE slug = 'floral-midi-dress'),
        'https://picsum.photos/seed/vibe_dress_thumb/600/800',
        '플로럴 미디 원피스 대표 썸네일',
        1,
        true
    ),
    (
        (SELECT id FROM public.products WHERE slug = 'floral-midi-dress'),
        'https://picsum.photos/seed/vibe_dress_detail1/600/800',
        '플로럴 미디 원피스 전신 착용컷',
        2,
        false
    );
