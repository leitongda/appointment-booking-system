# 📰 内容管理模块需求文档

## 一、模块概述

内容管理模块负责新闻资讯、公告、轮播图、弹框等内容的管理。

## 二、功能清单

### 2.1 新闻管理
- 新闻分类管理
- 新闻列表
- 新闻发布/编辑
- 新闻置顶

### 2.2 公告管理
- 公告列表
- 公告发布
- 公告类型（系统/停诊/活动）

### 2.3 轮播图管理
- 轮播图列表
- 上传/编辑轮播图
- 跳转链接配置
- 有效期设置

### 2.4 弹框管理
- 弹框列表
- 弹框配置
- 显示位置/频率设置
- 有效期设置

## 三、数据模型

### news_types 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR | 分类名称 |
| sort_order | INT | 排序 |
| status | SMALLINT | 状态 |

### news 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| type_id | UUID | 分类ID |
| title | VARCHAR | 标题 |
| summary | VARCHAR | 摘要 |
| content | TEXT | 内容 |
| cover_image | VARCHAR | 封面图 |
| is_top | BOOLEAN | 是否置顶 |
| publish_time | TIMESTAMP | 发布时间 |
| status | SMALLINT | 状态 |

### banners 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| title | VARCHAR | 标题 |
| image_url | VARCHAR | 图片地址 |
| link_url | VARCHAR | 跳转链接 |
| link_type | SMALLINT | 链接类型 |
| sort_order | INT | 排序 |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| status | SMALLINT | 状态 |

### popups 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| title | VARCHAR | 标题 |
| image_url | VARCHAR | 图片地址 |
| link_url | VARCHAR | 跳转链接 |
| position | VARCHAR | 显示位置 |
| frequency | VARCHAR | 显示频率 |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| status | SMALLINT | 状态 |

## 四、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /content/banners | 获取轮播图 |
| GET | /content/news | 获取新闻列表 |
| GET | /content/news/:id | 获取新闻详情 |
| GET | /content/notices | 获取公告列表 |
| GET | /content/popups | 获取弹框 |

