/**
 * 考勤管理
 *
 * 子菜单：
 *   - 班次管理（canAttendanceShifts）
 *   - 签到组管理（canAttendanceGroups）
 *   - 考勤规则（canAttendanceRules）
 *   - 考勤记录（canAttendanceRecords）
 *   - 公司每日记录（canAttendanceRecords, hideInMenu）
 *   - 假期管理（canAttendanceLeave）
 *
 * 顶层 access: canAttendance
 */
import type { IRoute } from '@umijs/max';

const attendanceRoutes: IRoute[] = [
  {
    path: '/attendance',
    name: '考勤管理',
    icon: 'ClockCircleOutlined',
    access: 'canAttendance',
    routes: [
      { path: '/attendance', redirect: '/attendance/shifts' },
      {
        path: '/attendance/shifts',
        name: '班次管理',
        component: '@/pages/attendance/shifts',
        access: 'canAttendanceShifts',
      },
      {
        path: '/attendance/shifts/create',
        name: '新增班次',
        component: '@/pages/attendance/shift-form',
        access: 'canAttendanceShifts',
        hideInMenu: true,
      },
      {
        path: '/attendance/shifts/:id/edit',
        name: '编辑班次',
        component: '@/pages/attendance/shift-form',
        access: 'canAttendanceShifts',
        hideInMenu: true,
      },
      {
        path: '/attendance/groups',
        name: '签到组管理',
        component: '@/pages/attendance/groups',
        access: 'canAttendanceGroups',
      },
      {
        path: '/attendance/groups/create',
        name: '新增签到组',
        component: '@/pages/attendance/group-form',
        access: 'canAttendanceGroups',
        hideInMenu: true,
      },
      {
        path: '/attendance/groups/:id/edit',
        name: '编辑签到组',
        component: '@/pages/attendance/group-form',
        access: 'canAttendanceGroups',
        hideInMenu: true,
      },
      {
        path: '/attendance/rules',
        name: '考勤规则',
        component: '@/pages/attendance/rules',
        access: 'canAttendanceRules',
      },
      {
        path: '/attendance/rules/create',
        name: '新增考勤规则',
        component: '@/pages/attendance/rule-form',
        access: 'canAttendanceRules',
        hideInMenu: true,
      },
      {
        path: '/attendance/rules/:id/edit',
        name: '编辑考勤规则',
        component: '@/pages/attendance/rule-form',
        access: 'canAttendanceRules',
        hideInMenu: true,
      },
      {
        path: '/attendance/records',
        name: '考勤记录',
        component: '@/pages/attendance/records',
        access: 'canAttendanceRecords',
      },
      {
        path: '/attendance/records/daily',
        name: '公司每日记录',
        component: '@/pages/attendance/daily-records',
        access: 'canAttendanceRecords',
        hideInMenu: true,
      },
      // NOTE: 假期管理 / 假期申请 pages (pages/attendance/leave, pages/attendance/leave-requests)
      // were never created — referencing them here breaks umi route resolution and aborts `dev`.
      // Commented out until the page components exist. See apps/admin/src/access.ts -> canAttendanceLeave.
      // {
      //   path: '/attendance/leave',
      //   name: '假期管理',
      //   component: '@/pages/attendance/leave',
      //   access: 'canAttendanceLeave',
      // },
      // {
      //   path: '/attendance/leave/requests',
      //   name: '假期申请',
      //   component: '@/pages/attendance/leave-requests',
      //   access: 'canAttendanceLeave',
      // },
    ],
  },
];

export default attendanceRoutes;
