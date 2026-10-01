-- ==============================================================================
-- Day 5 실습 마이그레이션: product_options 색상 x 사이즈 조합 지원
-- ==============================================================================

-- 1. product_options 테이블에 신규 컬럼 추가 (color, size, stock)
ALTER TABLE public.product_options 
ADD COLUMN IF NOT EXISTS color TEXT,
ADD COLUMN IF NOT EXISTS size TEXT,
ADD COLUMN IF NOT EXISTS stock INTEGER DEFAULT 0;

-- 2. 기존 옵션 컬럼(option_name, option_value)의 NOT NULL 제약조건 완화
-- (색상x사이즈 조합 행 추가 시 option_name/option_value가 없어도 입력 가능하도록 처리)
ALTER TABLE public.product_options 
ALTER COLUMN option_name DROP NOT NULL,
ALTER COLUMN option_value DROP NOT NULL;

-- 3. (product_id, color, size) 조건부 UNIQUE 인덱스 생성
-- color와 size가 모두 NULL이 아닌 유효 조합 행에 대해서만 중복을 방지하며,
-- 기존 name/value 기반 행(color 또는 size가 NULL)은 여러 개 등록되어도 충돌하지 않도록 보장합니다.
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_options_color_size
ON public.product_options (product_id, color, size)
WHERE color IS NOT NULL AND size IS NOT NULL;
