/**
 * 组织架构
 *
 * 子菜单：
 *   - 门店管理（canStore）
 *   - 科室管理（canDepartment）
 *   - 医疗配置（canMedicalConfig，含 booking-rules / booking-fields / booking-notice / patient-card / shift-types / rule-sets）
 *   - 员工管理（canUserManagement）
 *
 * 顶层 access: canOrganizationManagement
 */
const organization = [
  {
    path: '/organization',
    name: '组织架构',
    icon: 'apartment',
    access: 'canOrganizationManagement',
    routes: [
      { path: '/organization', redirect: '/organization/store' },
      {
        path: '/organization/store',
        name: '门店管理',
        icon: 'shop',
        access: 'canStore',
        routes: [
          { path: '/organization/store', redirect: '/organization/store/list' },
          { path: '/organization/store/list', name: '门店列表', component: './store' },
          { path: '/organization/store/create', name: '新增门店', component: './store/form', hideInMenu: true },
          { path: '/organization/store/:id/edit', name: '编辑门店', component: './store/form', hideInMenu: true },
          { path: '/organization/store/:storeId/fee-types', name: '门店诊费类型', redirect: '/medical-services/consultation-fee/types', hideInMenu: true },
          { path: '/organization/store/:storeId/fee-templates', name: '门店诊费模板', redirect: '/medical-services/consultation-fee/templates', hideInMenu: true },
          { path: '/organization/store/:storeId/visit-type-config', name: '复诊规则配置', component: './store/visit-type-config', hideInMenu: true },
        ],
      },
      {
        path: '/organization/department',
        name: '科室管理',
        icon: 'build',
        access: 'canDepartment',
        routes: [
          { path: '/organization/department', redirect: '/organization/department/list' },
          { path: '/organization/department/list', name: '科室列表', component: './department' },
          { path: '/organization/department/create', name: '新增科室', component: './department/form', hideInMenu: true },
          { path: '/organization/department/:id/edit', name: '编辑科室', component: './department/form', hideInMenu: true },
        ],
      },
      {
        path: '/organization/medical-config',
        name: '医疗配置',
        icon: 'tool',
        access: 'canMedicalConfig',
        routes: [
          { path: '/organization/medical-config', redirect: '/organization/medical-config/booking-rules' },
          { path: '/organization/medical-config/booking-rules', name: '预约规则', icon: 'clockCircle', component: './system/settings', access: 'canBookingRules' },
          { path: '/organization/medical-config/booking-fields', name: '预约字段', icon: 'orderedList', component: './system/settings', access: 'canBookingFields' },
          { path: '/organization/medical-config/booking-notice', name: '预约须知', icon: 'fileDone', component: './system/booking-notice', access: 'canBookingNotice' },
          { path: '/organization/medical-config/patient-card', name: '就诊卡配置', icon: 'idcard', component: './system/settings', access: 'canPatientCardConfig' },
          {
            path: '/organization/medical-config/shift-types',
            name: '班次类型',
            icon: 'clockCircle',
            access: 'canShiftTypes',
            routes: [
              { path: '/organization/medical-config/shift-types', component: './system/shift-types' },
              { path: '/organization/medical-config/shift-types/create', name: '新增班次类型', component: './system/shift-type-form', hideInMenu: true },
              { path: '/organization/medical-config/shift-types/:id/edit', name: '编辑班次类型', component: './system/shift-type-form', hideInMenu: true },
            ],
          },
          {
            path: '/organization/medical-config/rule-sets',
            name: '规则组管理',
            icon: 'cluster',
            access: 'canRuleSets',
            routes: [
              { path: '/organization/medical-config/rule-sets', component: './system/rule-sets' },
              { path: '/organization/medical-config/rule-sets/create', name: '新增规则组', component: './system/rule-set-form', hideInMenu: true },
              { path: '/organization/medical-config/rule-sets/:id/edit', name: '编辑规则组', component: './system/rule-set-form', hideInMenu: true },
              { path: '/organization/medical-config/rule-sets/:id/audit', name: '变更历史', component: './system/rule-set-audit', hideInMenu: true },
            ],
          },
        ],
      },
      {
        path: '/organization/staff',
        name: '员工管理',
        icon: 'userSwitch',
        access: 'canUserManagement',
        routes: [
          { path: '/organization/staff', component: './system/user' },
          { path: '/organization/staff/create', name: '新增员工', component: './system/user-form', hideInMenu: true },
          { path: '/organization/staff/:id/edit', name: '编辑员工', component: './system/user-form', hideInMenu: true },
        ],
      },
    ],
  },
];

export default organization;
