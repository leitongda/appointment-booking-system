import type { MenuDataItem } from '@ant-design/pro-components';

interface DynamicMenuConfig {
  pattern: RegExp;
  parentPath: string;
  menuItem: {
    name: string;
    path: string;
  };
}

const dynamicMenuRules: DynamicMenuConfig[] = [
  // 科室管理
  {
    pattern: /^\/organization\/department\/create$/,
    parentPath: '/organization/department',
    menuItem: { name: '新增科室', path: '/organization/department/create' },
  },
  {
    pattern: /^\/organization\/department\/[^/]+\/edit$/,
    parentPath: '/organization/department',
    menuItem: { name: '编辑科室', path: '/organization/department/:id/edit' },
  },
  // 门店管理
  {
    pattern: /^\/organization\/store\/create$/,
    parentPath: '/organization/store',
    menuItem: { name: '新增门店', path: '/organization/store/create' },
  },
  {
    pattern: /^\/organization\/store\/[^/]+\/edit$/,
    parentPath: '/organization/store',
    menuItem: { name: '编辑门店', path: '/organization/store/:id/edit' },
  },
  // 医生管理
  {
    pattern: /^\/medical-services\/doctor\/create$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '新增医生', path: '/medical-services/doctor/create' },
  },
  {
    pattern: /^\/medical-services\/doctor\/[^/]+\/edit$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '编辑医生', path: '/medical-services/doctor/:id/edit' },
  },
  {
    pattern: /^\/medical-services\/doctor\/(?!list$|create$|booking-setting)[^/]+$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '医生详情', path: '/medical-services/doctor/:id' },
  },
  // 预约设置
  {
    pattern: /^\/medical-services\/doctor\/booking-setting\/create$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '添加预约设置', path: '/medical-services/doctor/booking-setting/create' },
  },
  {
    pattern: /^\/medical-services\/doctor\/booking-setting\/[^/]+\/edit$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '编辑预约设置', path: '/medical-services/doctor/booking-setting/:id/edit' },
  },
  // 角色权限
  {
    pattern: /^\/system\/role\/create$/,
    parentPath: '/system/role',
    menuItem: { name: '新增角色', path: '/system/role/create' },
  },
  {
    pattern: /^\/system\/role\/[^/]+\/edit$/,
    parentPath: '/system/role',
    menuItem: { name: '编辑角色', path: '/system/role/:id/edit' },
  },
  {
    pattern: /^\/system\/role\/[^/]+\/permissions$/,
    parentPath: '/system/role',
    menuItem: { name: '分配权限', path: '/system/role/:id/permissions' },
  },
  // 员工管理
  {
    pattern: /^\/organization\/staff\/create$/,
    parentPath: '/organization/staff',
    menuItem: { name: '新增员工', path: '/organization/staff/create' },
  },
  {
    pattern: /^\/organization\/staff\/[^/]+\/edit$/,
    parentPath: '/organization/staff',
    menuItem: { name: '编辑员工', path: '/organization/staff/:id/edit' },
  },
];

export function processMenuData(menuData: MenuDataItem[], pathname: string): MenuDataItem[] {
  const matchedRule = dynamicMenuRules.find((rule) => rule.pattern.test(pathname));

  if (!matchedRule) {
    return menuData;
  }

  return menuData.map((item) => {
    if (item.path === matchedRule.parentPath) {
      const dynamicMenuItem: MenuDataItem = {
        name: matchedRule.menuItem.name,
        path: pathname,
        hideInMenu: false,
      };

      return {
        ...item,
        children: [...(item.children || []), dynamicMenuItem],
      };
    }

    if (item.children) {
      return {
        ...item,
        children: processMenuData(item.children, pathname),
      };
    }

    return item;
  });
}

export function computeParentOpenKeys(pathname: string): string[] {
  const segments = pathname.split('/').filter(Boolean);
  const keys: string[] = [];
  let current = '';
  for (let i = 0; i < segments.length - 1; i++) {
    current += '/' + segments[i];
    keys.push(current);
  }
  return keys;
}
