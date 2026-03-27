## 1. 数据库设计
- [x] 1.1 创建 schedule_generation_logs 表的 migration 文件
- [x] 1.2 创建 ScheduleGenerationLog model

## 2. 后端 API 开发
- [x] 2.1 创建 ScheduleGenerationLog schema
- [x] 2.2 实现生成历史记录服务
- [x] 2.3 新增批量删除排班 API (`POST /schedule-templates/{id}/batch-delete`)
- [x] 2.4 新增批量停诊 API (`POST /schedule-templates/{id}/batch-suspend`)
- [x] 2.5 新增检查已生成排班 API (`GET /schedule-templates/{id}/check-generated`)
- [x] 2.6 新增获取生成历史 API (`GET /schedule-templates/{id}/logs`)
- [x] 2.7 修改生成排班 API，增加记录日志功能

## 3. 前端 API 封装
- [x] 3.1 新增 scheduleTemplateApi 方法：batchDelete, batchSuspend, checkGenerated, getLogs

## 4. 排班规则页面改造
- [x] 4.1 添加一键删除排班按钮和确认弹窗
- [x] 4.2 添加一键停诊按钮和确认弹窗
- [x] 4.3 生成排班时增加重复生成确认机制
- [x] 4.4 添加查看历史记录弹窗

## 5. 排班列表页面改造
- [x] 5.1 添加日期范围搜索组件

