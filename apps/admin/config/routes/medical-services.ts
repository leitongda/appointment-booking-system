/**
 * 医疗服务（核心业务域）
 *
 * 子菜单：
 *   - 医生管理（canDoctor）
 *   - 排班管理（canSchedule，含 canLeaveRequest）
 *   - 预约管理（canAppointment，含候补队列）
 *   - 患者管理（canPatient）
 *   - 病历管理（canMedicalRecord）
 *   - 检查报告（canAppointment）
 *   - 诊费管理（canConsultationFee）
 *
 * 顶层 access: canClinicalOperations
 */
const medicalServices = [
  {
    path: '/medical-services',
    name: '医疗服务',
    icon: 'medicineBox',
    access: 'canClinicalOperations',
    routes: [
      { path: '/medical-services', redirect: '/medical-services/doctor' },
      {
        path: '/medical-services/doctor',
        name: '医生管理',
        icon: 'user',
        access: 'canDoctor',
        routes: [
          { path: '/medical-services/doctor', redirect: '/medical-services/doctor/list' },
          { path: '/medical-services/doctor/list', name: '医生列表', component: './doctor/list' },
          { path: '/medical-services/doctor/booking-setting', name: '预约设置', component: './doctor/booking-setting' },
          { path: '/medical-services/doctor/booking-setting/create', name: '添加预约设置', component: './doctor/booking-setting-form', hideInMenu: true },
          { path: '/medical-services/doctor/booking-setting/:id/edit', name: '编辑预约设置', component: './doctor/booking-setting-form', hideInMenu: true },
          { path: '/medical-services/doctor/create', name: '新增医生', component: './doctor/form', hideInMenu: true },
          { path: '/medical-services/doctor/:id', name: '医生详情', component: './doctor/detail', hideInMenu: true },
          { path: '/medical-services/doctor/:id/edit', name: '编辑医生', component: './doctor/form', hideInMenu: true },
        ],
      },
      {
        path: '/medical-services/schedule',
        name: '排班管理',
        icon: 'calendar',
        access: 'canSchedule',
        routes: [
          { path: '/medical-services/schedule', redirect: '/medical-services/schedule/rule' },
          { path: '/medical-services/schedule/rule', name: '排班规则设置', component: './schedule/rule' },
          { path: '/medical-services/schedule/rule/create', name: '新增排班规则', component: './schedule/rule/form', hideInMenu: true },
          { path: '/medical-services/schedule/rule/:id/edit', name: '编辑排班规则', component: './schedule/rule/form', hideInMenu: true },
          { path: '/medical-services/schedule/list', name: '排班列表', component: './schedule/detail' },
          { path: '/medical-services/schedule/calendar', name: '排班日历', component: './schedule/calendar' },
          { path: '/medical-services/schedule/gantt', name: '排班甘特图', component: './schedule/gantt' },
          { path: '/medical-services/schedule/custom', name: '自定义排班', component: './schedule/custom' },
          { path: '/medical-services/schedule/custom/create', name: '添加自定义排班', component: './schedule/custom-form', hideInMenu: true },
          { path: '/medical-services/schedule/rest-day', name: '休息日设置', component: './schedule/rest-day' },
          { path: '/medical-services/schedule/rest-day/create', name: '添加休息日', component: './schedule/rest-day-form', hideInMenu: true },
          { path: '/medical-services/schedule/suspension', name: '停诊管理', component: './schedule/suspension' },
          { path: '/medical-services/schedule/leave-request', name: '停诊审核', component: './leave-request', access: 'canLeaveRequest' },
          { path: '/medical-services/schedule/extra-quota', name: '加号管理', component: './schedule/extra-quota', access: 'canSchedule' },
          { path: '/medical-services/schedule/room', name: '诊室管理', component: './schedule/room', access: 'canSchedule' },
          { path: '/medical-services/schedule/statistics', name: '排班统计', component: './schedule/statistics' },
        ],
      },
      {
        path: '/medical-services/appointment',
        name: '预约管理',
        icon: 'schedule',
        access: 'canAppointment',
        routes: [
          { path: '/medical-services/appointment', redirect: '/medical-services/appointment/list' },
          { path: '/medical-services/appointment/list', name: '预约列表', component: './appointment/list' },
          { path: '/medical-services/appointment/queue', name: '签到队列', component: './appointment/queue' },
          { path: '/medical-services/appointment/statistics', name: '预约统计', component: './appointment/statistics' },
          { path: '/medical-services/appointment/:id', name: '预约详情', component: './appointment/detail', hideInMenu: true },
          { path: '/medical-services/appointment/waitlist', name: '候补队列', component: './waitlist' },
        ],
      },
      {
        path: '/medical-services/patient',
        name: '患者管理',
        icon: 'usergroupAdd',
        access: 'canPatient',
        routes: [
          { path: '/medical-services/patient', redirect: '/medical-services/patient/list' },
          { path: '/medical-services/patient/list', name: '患者列表', component: './user' },
          { path: '/medical-services/patient/:id', name: '患者详情', component: './user/detail', hideInMenu: true },
          { path: '/medical-services/patient/card/list', name: '就诊卡列表', component: './patient' },
          { path: '/medical-services/patient/card/:id', name: '就诊卡详情', component: './patient/detail', hideInMenu: true },
        ],
      },
      {
        path: '/medical-services/medical-record',
        name: '病历管理',
        icon: 'fileProtect',
        component: './medical-record',
        access: 'canMedicalRecord',
      },
      {
        path: '/medical-services/examination-report',
        name: '检查报告',
        icon: 'fileSearch',
        component: './examination-report',
        access: 'canAppointment',
      },
      {
        path: '/medical-services/follow-up',
        name: '诊后随访',
        icon: 'heart',
        access: 'canMedicalRecord',
        routes: [
          { path: '/medical-services/follow-up', redirect: '/medical-services/follow-up/tasks' },
          { path: '/medical-services/follow-up/plans', name: '随访计划', component: './follow-up/plans' },
          { path: '/medical-services/follow-up/tasks', name: '随访任务', component: './follow-up/tasks' },
          { path: '/medical-services/follow-up/records', name: '随访记录', component: './follow-up/records' },
          { path: '/medical-services/follow-up/statistics', name: '随访统计', component: './follow-up/statistics' },
        ],
      },
      {
        path: '/medical-services/consultation-fee',
        name: '诊费管理',
        icon: 'dollarCircle',
        access: 'canConsultationFee',
        routes: [
          { path: '/medical-services/consultation-fee', redirect: '/medical-services/consultation-fee/types' },
          { path: '/medical-services/consultation-fee/types', name: '诊费类型', component: './system/consultation-fee-types' },
          { path: '/medical-services/consultation-fee/types/create', name: '新增诊费类型', component: './system/consultation-fee-type-form', hideInMenu: true },
          { path: '/medical-services/consultation-fee/types/:id/edit', name: '编辑诊费类型', component: './system/consultation-fee-type-form', hideInMenu: true },
          { path: '/medical-services/consultation-fee/templates', name: '诊费模板', component: './system/consultation-fee-templates' },
        ],
      },
    ],
  },
];

export default medicalServices;
