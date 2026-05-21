/**
 * 审批中心
 *
 * URL 前缀：`/approval`
 *
 * 子菜单：
 *   - 审批中心（我的待办/已办/发起的）
 *   - 流程定义管理
 *
 * 顶层 access: canApproval
 */
const approval = [
  {
    path: '/approval',
    name: '审批中心',
    icon: 'audit',
    access: 'canApproval',
    routes: [
      { path: '/approval', redirect: '/approval/instances' },
      {
        path: '/approval/instances',
        name: '审批中心',
        component: './approval/instances',
      },
      {
        path: '/approval/instances/:id',
        name: '审批详情',
        component: './approval/instances/detail',
        hideInMenu: true,
      },
      {
        path: '/approval/definitions',
        name: '流程定义',
        component: './approval/definitions',
        access: 'canApprovalFlowManage',
      },
    ],
  },
];

export default approval;
