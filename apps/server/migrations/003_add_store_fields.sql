-- 门店表新增字段
-- Migration: 003_add_store_fields
-- Description: 添加门店密码、邮箱、logo、风格选择字段

-- 添加门店密码字段
ALTER TABLE stores ADD COLUMN password VARCHAR(100) COMMENT '门店密码';

-- 添加邮箱字段
ALTER TABLE stores ADD COLUMN email VARCHAR(100) COMMENT '邮箱';

-- 添加门店logo字段
ALTER TABLE stores ADD COLUMN logo VARCHAR(255) COMMENT '门店logo';

-- 添加风格选择字段
ALTER TABLE stores ADD COLUMN theme_style VARCHAR(50) COMMENT '风格选择';
