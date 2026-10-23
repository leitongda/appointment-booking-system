-- P3-1 内容表 tenant_id 回填（由 p3a1_content_tenant 迁移读取执行）
-- 仅按门店归属回填；store_id IS NULL 的平台级内容保持 tenant_id = NULL
UPDATE news
SET tenant_id = (SELECT s.tenant_id FROM stores s WHERE s.id = news.store_id)
WHERE news.store_id IS NOT NULL
  AND news.tenant_id IS NULL;

UPDATE notices
SET tenant_id = (SELECT s.tenant_id FROM stores s WHERE s.id = notices.store_id)
WHERE notices.store_id IS NOT NULL
  AND notices.tenant_id IS NULL;

UPDATE banners
SET tenant_id = (SELECT s.tenant_id FROM stores s WHERE s.id = banners.store_id)
WHERE banners.store_id IS NOT NULL
  AND banners.tenant_id IS NULL;
