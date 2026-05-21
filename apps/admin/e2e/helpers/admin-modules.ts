export interface AdminModuleRoute {
  path: string;
  label?: string;
}

export interface AdminModuleGroup {
  key: string;
  name: string;
  routes: AdminModuleRoute[];
}

export const adminModuleGroups: AdminModuleGroup[] = [
  {
    key: 'dashboard',
    name: '仪表盘',
    routes: [
      { path: '/dashboard', label: '仪表盘' },
    ],
  },
  {
    key: 'platform',
    name: '平台管理',
    routes: [
      { path: '/platform/tenant/list', label: '租户列表' },
      { path: '/platform/tenant/plans', label: '订阅计划' },
      { path: '/platform/miniapp-platform/company' },
      { path: '/platform/miniapp-platform/payment-profile' },
      { path: '/platform/miniapp-platform/instance' },
      { path: '/platform/miniapp-platform/template' },
      { path: '/platform/miniapp-platform/build' },
      { path: '/platform/miniapp-platform/release' },
    ],
  },
  {
    key: 'medical-services',
    name: '医疗服务',
    routes: [
      { path: '/medical-services/doctor/list', label: '医生列表' },
      { path: '/medical-services/doctor/booking-setting', label: '预约设置' },
      { path: '/medical-services/schedule/rule', label: '排班规则设置' },
      { path: '/medical-services/schedule/list', label: '排班列表' },
      { path: '/medical-services/schedule/calendar', label: '排班日历' },
      { path: '/medical-services/schedule/gantt', label: '排班甘特图' },
      { path: '/medical-services/schedule/custom', label: '自定义排班' },
      { path: '/medical-services/schedule/rest-day', label: '休息日设置' },
      { path: '/medical-services/schedule/suspension', label: '停诊管理' },
      { path: '/medical-services/schedule/leave-request', label: '停诊审核' },
      { path: '/medical-services/schedule/statistics', label: '排班统计' },
      { path: '/medical-services/appointment/list', label: '预约列表' },
      { path: '/medical-services/appointment/queue', label: '签到队列' },
      { path: '/medical-services/appointment/statistics', label: '预约统计' },
      { path: '/medical-services/appointment/waitlist', label: '候补队列' },
      { path: '/medical-services/patient/list', label: '患者列表' },
      { path: '/medical-services/patient/card/list', label: '就诊卡列表' },
      { path: '/medical-services/medical-record', label: '病历管理' },
      { path: '/medical-services/consultation-fee/types', label: '诊费类型' },
      { path: '/medical-services/consultation-fee/templates', label: '诊费模板' },
      { path: '/medical-services/examination-report', label: '检查报告' },
    ],
  },
  {
    key: 'finance',
    name: '财务中心',
    routes: [
      { path: '/finance/payment', label: '支付查询' },
      { path: '/finance/refund', label: '退款管理' },
    ],
  },
  {
    key: 'organization',
    name: '组织架构',
    routes: [
      { path: '/organization/store/list', label: '门店列表' },
      { path: '/organization/department/list', label: '科室列表' },
      { path: '/organization/medical-config/booking-rules', label: '预约规则' },
      { path: '/organization/medical-config/booking-fields', label: '预约字段' },
      { path: '/organization/medical-config/booking-notice', label: '预约须知' },
      { path: '/organization/medical-config/patient-card', label: '就诊卡配置' },
      { path: '/organization/medical-config/shift-types', label: '班次类型' },
      { path: '/organization/medical-config/rule-sets', label: '规则组管理' },
      { path: '/organization/staff', label: '员工管理' },
    ],
  },
  {
    key: 'content-center',
    name: '运营中心',
    routes: [
      { path: '/content-center/content/news', label: '新闻管理' },
      { path: '/content-center/content/notice', label: '公告管理' },
      { path: '/content-center/content/banner', label: '轮播图' },
      { path: '/content-center/message/list', label: '消息列表' },
      { path: '/content-center/feedback', label: '用户反馈' },
      { path: '/content-center/statistics', label: '数据统计' },
    ],
  },
  {
    key: 'system',
    name: '系统管理',
    routes: [
      { path: '/system/role', label: '角色列表' },
      { path: '/system/config/hospital-info', label: '医院信息' },
      { path: '/system/config/wechat', label: '微信配置' },
      { path: '/system/config/email-config', label: '邮件配置' },
      { path: '/system/config/image-config', label: '图片配置' },
      { path: '/system/config/email-templates', label: '邮件模板' },
      { path: '/system/config/email-recipients', label: '邮件接收人' },
      { path: '/system/blacklist', label: '黑名单管理' },
      { path: '/system/monitoring/log', label: '操作日志' },
      { path: '/system/monitoring/notification-logs', label: '通知日志' },
      { path: '/system/monitoring/checkin-audit-logs', label: '签到审计' },
      { path: '/system/monitoring/online-users', label: '在线用户' },
    ],
  },
];

export const adminModuleGroupMap = Object.fromEntries(
  adminModuleGroups.map((group) => [group.key, group]),
) as Record<string, AdminModuleGroup>;
