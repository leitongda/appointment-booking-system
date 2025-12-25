-- 修复排班表中缺失的 store_id
-- 根据医生的 store_id 来补充排班的 store_id

UPDATE schedules s
SET store_id = (
    SELECT d.store_id 
    FROM doctors d 
    WHERE d.id = s.doctor_id
)
WHERE s.store_id IS NULL;

