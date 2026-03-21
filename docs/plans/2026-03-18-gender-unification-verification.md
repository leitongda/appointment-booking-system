# 性别枚举统一回归清单

## 统一标准

- `0 = 未知`
- `1 = 男`
- `2 = 女`

当前目标是确认这套标准在以下三条链路里一致：

- admin 患者/用户管理
- admin 医生管理
- patient-miniapp 患者编辑

并确认历史医生数据已经通过迁移从旧语义切到新语义。

## 前置条件

### 1. 执行数据库迁移

先执行：

```bash
cd apps/server
alembic upgrade head
```

本次相关迁移：

- [038_unify_doctor_gender_enum.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/migrations/versions/038_unify_doctor_gender_enum.py)

### 2. 已完成的静态检查

已验证通过：

```bash
pnpm --filter @hospital/patient-miniapp exec tsc --noEmit --skipLibCheck
python3 -m py_compile \
  apps/server/app/models/doctor.py \
  apps/server/app/schemas/doctor.py \
  apps/server/app/modules/doctors/router.py \
  apps/server/app/modules/doctors/service_mutation.py \
  apps/server/app/modules/auth/router.py \
  apps/server/app/modules/import_export/router_import.py \
  apps/server/app/modules/import_export/router_export.py \
  apps/server/app/modules/import_export/router_template.py \
  apps/server/migrations/versions/038_unify_doctor_gender_enum.py
```

## 最短回归步骤

### A. Admin 患者管理

入口：

- [patient/index.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/admin/src/pages/patient/index.tsx)
- [patient/detail.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/admin/src/pages/patient/detail.tsx)
- [user/detail.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/admin/src/pages/user/detail.tsx)

操作：

1. 打开一个 `gender=0` 的患者。
   预期：列表、详情、头部卡片都显示“未知”。
2. 在“编辑就诊卡信息”里打开性别选择。
   预期：当前值定位到“未知”，不是空，也不是“女”。
3. 保存不改值。
   预期：保存后仍为 `0`，页面显示仍是“未知”。
4. 切成“女”后保存。
   预期：保存后显示“女”，后端值为 `2`。
5. 在“患者详情 -> 亲友编辑”里重复一次。
   预期：亲友性别同样正确。
6. 打开“用户详情 -> 编辑用户信息”。
   预期：`gender=0` 显示“未知”，`1/2` 分别显示“男/女”。

### B. Admin 医生管理

入口：

- [doctor/form.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/admin/src/pages/doctor/form.tsx)
- [doctor/list.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/admin/src/pages/doctor/list.tsx)

操作：

1. 打开一个历史女性医生数据。
   预期：如果已执行迁移，列表显示为“女”，不是“未知”。
2. 打开医生编辑页。
   预期：性别选择里有“未知/男/女”三项。
3. 新增医生时不手选性别直接保存。
   预期：默认值为“未知”，后端存 `0`。
4. 分别保存“男”“女”后回到列表。
   预期：列表显示与详情一致，值分别为 `1/2`。

### C. 小程序患者编辑

入口：

- [patient/edit.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/patient-miniapp/src/packageProfile/pages/patient/edit.tsx)
- [profile/edit.tsx](/Users/leijiadashao/leitond/appointment-booking-system/apps/patient-miniapp/src/packageProfile/pages/profile/edit.tsx)

操作：

1. 新建就诊人。
   预期：默认性别为“未知/不透露”，不是“男”。
2. 编辑已有 `gender=0` 的就诊人。
   预期：picker 定位到“未知/不透露”。
3. 编辑已有 `gender=2` 的就诊人。
   预期：picker 定位到“女”。
4. 编辑用户资料中的性别。
   预期：`0/1/2` 对应“保密/男/女”。

### D. 导入导出

入口：

- [router_import.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/modules/import_export/router_import.py)
- [router_export.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/modules/import_export/router_export.py)
- [router_template.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/modules/import_export/router_template.py)

操作：

1. 下载医生导入模板。
   预期：模板字段说明显示“未知/男/女”。
2. 构造一条医生 Excel，性别填“未知”。
   预期：导入成功，医生性别为 `0`。
3. 导出医生列表。
   预期：`0/1/2` 分别导出为“未知/男/女”。

## 数据检查建议

迁移后，可直接抽样查库确认：

```sql
SELECT gender, COUNT(*)
FROM doctors
GROUP BY gender
ORDER BY gender;
```

预期：

- 不应再把旧女性数据保留为旧语义
- 新语义下允许出现 `0/1/2`

如果要专门确认历史女医生迁移是否生效，可在迁移前后比对一批已知女性医生记录。

## 风险点

### 1. 迁移未执行

现象：

- 医生旧数据中的 `0` 会显示成“未知”

结论：

- 这不是前端 bug，是数据库还没迁

### 2. 只测了展示，没测保存

现象：

- 页面显示正确，但保存后值被写错

结论：

- 至少要对患者、用户、医生各做一次“打开表单 -> 保存 -> 刷新 -> 再打开表单”的闭环验证

### 3. Excel 模板和导入导出漏验

现象：

- 页面没问题，但运营导表会把“未知”丢掉

结论：

- 医生导入导出必须单独验一次
