-- 添加预约提醒相关字段
-- 用于 Celery 定时任务发送预约提醒

ALTER TABLE appointments 
ADD COLUMN IF NOT EXISTS reminder_sent INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMP;

COMMENT ON COLUMN appointments.reminder_sent IS '是否已发送提醒: 0否 1是';
COMMENT ON COLUMN appointments.reminder_sent_at IS '提醒发送时间';

-- 创建索引以优化定时任务查询
CREATE INDEX IF NOT EXISTS idx_appointments_reminder 
ON appointments(status, reminder_sent, schedule_id);

