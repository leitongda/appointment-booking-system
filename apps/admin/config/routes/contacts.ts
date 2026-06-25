/**
 * 通讯录管理
 *
 * URL 前缀：`/contacts`
 *
 * 子菜单：
 *   - 联系人管理（canContacts）
 *   - 渠道账号管理（canContacts）
 *
 * 顶层 access: canContacts
 */
const contacts = [
  {
    path: '/contacts',
    name: '通讯录',
    icon: 'contacts',
    access: 'canContacts',
    routes: [
      { path: '/contacts', redirect: '/contacts/list' },
      { path: '/contacts/list', name: '联系人管理', component: './contacts' },
      { path: '/contacts/channels', name: '渠道账号管理', component: './contacts/channels' },
    ],
  },
];

export default contacts;
