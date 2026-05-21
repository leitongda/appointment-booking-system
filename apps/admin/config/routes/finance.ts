/**
 * 财务中心
 *
 * 子菜单：
 *   - 支付查询（canPayment）
 *   - 退款管理（canRefund）
 *
 * 顶层 access: canFinanceManagement
 */
const finance = [
  {
    path: '/finance',
    name: '财务中心',
    icon: 'accountBook',
    access: 'canFinanceManagement',
    routes: [
      { path: '/finance', redirect: '/finance/payment' },
      {
        path: '/finance/payment',
        name: '支付查询',
        icon: 'transaction',
        component: './payment',
        access: 'canPayment',
      },
      {
        path: '/finance/refund',
        name: '退款管理',
        icon: 'refund',
        component: './refund',
        access: 'canRefund',
      },
    ],
  },
];

export default finance;
