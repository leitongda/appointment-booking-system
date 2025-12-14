-- 医生表新增字段迁移脚本
-- 执行前请确保数据库已备份

-- 添加门店关联字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS store_id VARCHAR(36);
ALTER TABLE doctors ADD CONSTRAINT fk_doctors_store_id FOREIGN KEY (store_id) REFERENCES stores(id);
CREATE INDEX IF NOT EXISTS ix_doctors_store_id ON doctors(store_id);

-- 添加登录账号字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS username VARCHAR(50);
CREATE UNIQUE INDEX IF NOT EXISTS ix_doctors_username ON doctors(username);

-- 添加性别字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS gender INTEGER DEFAULT 1;

-- 添加banner图字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS banner VARCHAR(255);

-- 添加医龄字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS years_of_experience INTEGER DEFAULT 0;

-- 添加资质信息字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS education VARCHAR(50);
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS graduate_school VARCHAR(100);
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS license_number VARCHAR(100);
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS license_image VARCHAR(255);
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS honors TEXT;

-- 添加坐诊设置字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS schedule_desc VARCHAR(255);
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS max_daily_appointments INTEGER DEFAULT 0;
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS online_consult_enabled INTEGER DEFAULT 0;
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS online_consult_fee NUMERIC(10, 2) DEFAULT 0;

-- 添加展示设置字段
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS page_style INTEGER DEFAULT 1;
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS promo_video VARCHAR(255);
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS tags VARCHAR(255);

-- 验证字段是否添加成功
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'doctors' 
ORDER BY ordinal_position;

