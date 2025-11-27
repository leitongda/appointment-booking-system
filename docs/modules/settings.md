# ⚙️ 系统设置模块需求文档

## 一、模块概述

系统设置模块负责预约规则、微信配置、首页菜单等系统级配置管理。

## 二、功能清单

### 2.1 预约设置
- 预约提前天数
- 是否允许当天预约
- 取消预约规则
- 每人每天预约限制
- 爽约黑名单规则

### 2.2 微信设置
- 小程序 AppID/Secret
- 微信支付配置
- 消息模板配置

### 2.3 首页菜单
- 首页快捷入口配置
- 底部Tab菜单配置

### 2.4 预约须知
- 预约须知内容
- 就诊须知内容
- 退款说明

## 三、配置项说明

### 3.1 预约设置
| 配置项 | 键名 | 默认值 | 说明 |
|--------|------|--------|------|
| 预约提前天数 | booking_advance_days | 14 | 可提前预约的天数 |
| 当天预约 | booking_same_day | true | 是否允许当天预约 |
| 取消时限 | booking_cancel_hours | 2 | 就诊前N小时不可取消 |
| 每日限制 | booking_per_day_limit | 3 | 每人每天最多预约次数 |
| 爽约阈值 | no_show_blacklist_count | 3 | 爽约N次进入黑名单 |

### 3.2 微信设置
| 配置项 | 键名 | 说明 |
|--------|------|------|
| 小程序AppID | wechat_app_id | 微信小程序AppID |
| 小程序Secret | wechat_app_secret | 微信小程序密钥 |
| 商户号 | wechat_mch_id | 微信支付商户号 |
| 支付密钥 | wechat_api_key | 微信支付API密钥 |

## 四、数据模型

### settings 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| key | VARCHAR | 配置键(唯一) |
| value | TEXT | 配置值 |
| group_name | VARCHAR | 分组 |
| description | VARCHAR | 描述 |

### home_menus 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR | 名称 |
| icon | VARCHAR | 图标 |
| link_url | VARCHAR | 链接 |
| sort_order | INT | 排序 |
| status | SMALLINT | 状态 |

### tab_menus 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR | 名称 |
| icon | VARCHAR | 图标 |
| active_icon | VARCHAR | 选中图标 |
| path | VARCHAR | 路径 |
| sort_order | INT | 排序 |
| status | SMALLINT | 状态 |

## 五、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /settings | 获取所有设置(管理员) |
| PUT | /settings | 批量更新设置 |
| GET | /settings/booking | 获取预约设置(公开) |
| GET | /settings/home-menus | 获取首页菜单 |
| GET | /settings/tab-menus | 获取底部菜单 |
| GET | /settings/booking-notices | 获取预约须知 |

