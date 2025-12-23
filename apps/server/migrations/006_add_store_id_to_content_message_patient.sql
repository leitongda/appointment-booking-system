-- 为内容管理、消息、患者表添加门店关联字段
-- Migration: 006_add_store_id_to_content_message_patient

-- 新闻表添加门店ID
ALTER TABLE news ADD COLUMN store_id VARCHAR(36) NULL COMMENT '所属门店ID，NULL表示全局';
ALTER TABLE news ADD INDEX idx_news_store_id (store_id);
ALTER TABLE news ADD CONSTRAINT fk_news_store FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL;

-- 公告表添加门店ID
ALTER TABLE notices ADD COLUMN store_id VARCHAR(36) NULL COMMENT '所属门店ID，NULL表示全局';
ALTER TABLE notices ADD INDEX idx_notices_store_id (store_id);
ALTER TABLE notices ADD CONSTRAINT fk_notices_store FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL;

-- 轮播图表添加门店ID
ALTER TABLE banners ADD COLUMN store_id VARCHAR(36) NULL COMMENT '所属门店ID，NULL表示全局';
ALTER TABLE banners ADD INDEX idx_banners_store_id (store_id);
ALTER TABLE banners ADD CONSTRAINT fk_banners_store FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL;

-- 消息表添加门店ID
ALTER TABLE messages ADD COLUMN store_id VARCHAR(36) NULL COMMENT '所属门店ID，NULL表示全局';
ALTER TABLE messages ADD INDEX idx_messages_store_id (store_id);
ALTER TABLE messages ADD CONSTRAINT fk_messages_store FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL;

-- 患者表添加门店ID（首次就诊门店）
ALTER TABLE patients ADD COLUMN store_id VARCHAR(36) NULL COMMENT '首次就诊门店ID';
ALTER TABLE patients ADD INDEX idx_patients_store_id (store_id);
ALTER TABLE patients ADD CONSTRAINT fk_patients_store FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL;

