# 🏥 科室管理模块需求文档

## 一、模块概述

科室管理模块负责医院科室的创建、维护和组织结构管理。

## 二、功能清单

### 2.1 科室列表
- 科室树形结构展示
- 科室搜索
- 科室排序

### 2.2 科室信息
- 基本信息：名称、编码、图标
- 简介描述
- 关联门店
- 是否热门科室

### 2.3 科室状态
- 启用/停用
- 是否支持挂号

## 三、科室分类

支持两级科室结构：
- 一级科室：大类（如内科、外科）
- 二级科室：细分（如心内科、消化内科）

## 四、数据模型

### departments 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| hospital_id | UUID | 医院ID |
| branch_id | UUID | 门店ID |
| parent_id | UUID | 父科室ID |
| name | VARCHAR | 科室名称 |
| code | VARCHAR | 科室编码 |
| icon | VARCHAR | 图标 |
| description | TEXT | 简介 |
| sort_order | INT | 排序 |
| is_hot | BOOLEAN | 是否热门 |
| status | SMALLINT | 状态 |

## 五、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /departments | 获取科室列表 |
| GET | /departments/:id | 获取科室详情 |
| GET | /departments/tree | 获取科室树 |
| GET | /departments/hot | 获取热门科室 |
| POST | /departments | 创建科室 |
| PUT | /departments/:id | 更新科室 |
| DELETE | /departments/:id | 删除科室 |

