import type { Permission } from '@hospital/api';

export type PermissionControlType = 'page' | 'tab' | 'action' | 'api';

export interface PermissionViewNode extends Permission {
  children?: PermissionViewNode[];
  depth: number;
  moduleCode: string;
  moduleName: string;
  controlType: PermissionControlType;
  descendantCodes: string[];
}

export const CONTROL_TYPE_ORDER: PermissionControlType[] = ['page', 'tab', 'action', 'api'];

export const CONTROL_TYPE_LABELS: Record<PermissionControlType, string> = {
  page: '页面',
  tab: 'Tab / 视图',
  action: '按钮 / 操作',
  api: '接口 / 数据',
};

const ACTION_SEGMENTS = new Set([
  'create',
  'update',
  'delete',
  'approve',
  'refund',
  'send',
  'reply',
  'reset-password',
  'manage',
  'cancel',
  'bind',
  'import',
  'batch',
  'sort',
  'kick',
  'generate-username',
  'check-username',
  'check-unique',
  'status',
]);

const API_SEGMENTS = new Set([
  'list',
  'detail',
  'view',
  'export',
  'statistics',
  'all',
  'history',
]);

const HIGH_RISK_SEGMENTS = new Set([
  'delete',
  'refund',
  'reset-password',
  'permission',
  'kick',
  'status',
]);

export const createEmptyTypeCount = (): Record<PermissionControlType, number> => ({
  page: 0,
  tab: 0,
  action: 0,
  api: 0,
});

const getLastCodeSegment = (code: string): string => {
  const segments = code.split(':');
  return segments[segments.length - 1];
};

export const inferPermissionControlType = (
  permission: Permission,
  depth: number,
): PermissionControlType => {
  if (permission.controlType) {
    return permission.controlType;
  }

  const lastSegment = getLastCodeSegment(permission.code);
  const hasChildren = !!permission.children?.length;

  if (depth === 0) {
    return 'page';
  }

  if (hasChildren) {
    return 'tab';
  }

  if (ACTION_SEGMENTS.has(lastSegment)) {
    return 'action';
  }

  if (API_SEGMENTS.has(lastSegment)) {
    return 'api';
  }

  if (depth === 1 || permission.type === 'menu') {
    return 'tab';
  }

  return 'action';
};

export const normalizePermissionsTree = (
  permissions: Permission[],
  depth = 0,
  moduleCode?: string,
  moduleName?: string,
): PermissionViewNode[] => {
  return permissions.map((permission) => {
    const currentModuleCode = moduleCode || permission.code;
    const currentModuleName = moduleName || permission.name;
    const children = normalizePermissionsTree(
      permission.children || [],
      depth + 1,
      currentModuleCode,
      currentModuleName,
    );
    const controlType = inferPermissionControlType(permission, depth);
    const descendantCodes = [permission.code, ...children.flatMap((item) => item.descendantCodes)];

    return {
      ...permission,
      children,
      depth,
      moduleCode: currentModuleCode,
      moduleName: currentModuleName,
      controlType,
      descendantCodes,
    };
  });
};

export const getAllKeys = (permissions: Array<Permission | PermissionViewNode>): string[] => {
  const keys: string[] = [];

  const traverse = (nodes: Array<Permission | PermissionViewNode>) => {
    nodes.forEach((node) => {
      keys.push(node.code);
      if (node.children?.length) {
        traverse(node.children);
      }
    });
  };

  traverse(permissions);
  return keys;
};

export const collectPermissionCodes = (permissions: PermissionViewNode[]): string[] => {
  const codes: string[] = [];

  const traverse = (nodes: PermissionViewNode[]) => {
    nodes.forEach((node) => {
      codes.push(node.code);
      if (node.children?.length) {
        traverse(node.children);
      }
    });
  };

  traverse(permissions);
  return codes;
};

export const filterPermissionsTree = (
  permissions: PermissionViewNode[],
  options: {
    keyword: string;
    controlTypes: PermissionControlType[];
    checkedKeys: Set<string>;
    onlySelected: boolean;
  },
): PermissionViewNode[] => {
  const keyword = options.keyword.trim().toLowerCase();
  const controlTypeSet = new Set(options.controlTypes);

  const traverse = (nodes: PermissionViewNode[]): PermissionViewNode[] => {
    return nodes.reduce<PermissionViewNode[]>((result, node) => {
      const children = node.children?.length ? traverse(node.children) : [];
      const matchesKeyword =
        !keyword ||
        node.name.toLowerCase().includes(keyword) ||
        node.code.toLowerCase().includes(keyword);
      const matchesType = controlTypeSet.has(node.controlType);
      const matchesSelected = !options.onlySelected || options.checkedKeys.has(node.code);
      const matchesSelf = matchesKeyword && matchesType && matchesSelected;

      if (matchesSelf || children.length > 0) {
        result.push({
          ...node,
          children,
          descendantCodes: [node.code, ...children.flatMap((item) => item.descendantCodes)],
        });
      }

      return result;
    }, []);
  };

  return traverse(permissions);
};

export const countSelectedByControlType = (
  permissions: PermissionViewNode[],
  checkedKeys: Set<string>,
): Record<PermissionControlType, number> => {
  const summary = createEmptyTypeCount();

  const traverse = (nodes: PermissionViewNode[]) => {
    nodes.forEach((node) => {
      if (checkedKeys.has(node.code)) {
        summary[node.controlType] += 1;
      }
      if (node.children?.length) {
        traverse(node.children);
      }
    });
  };

  traverse(permissions);
  return summary;
};

export const countVisibleByControlType = (
  permissions: PermissionViewNode[],
): Record<PermissionControlType, number> => {
  const summary = createEmptyTypeCount();

  const traverse = (nodes: PermissionViewNode[]) => {
    nodes.forEach((node) => {
      summary[node.controlType] += 1;
      if (node.children?.length) {
        traverse(node.children);
      }
    });
  };

  traverse(permissions);
  return summary;
};

export const countCoveredModules = (
  permissions: PermissionViewNode[],
  checkedKeys: Set<string>,
): number => {
  return permissions.filter((module) => module.descendantCodes.some((code) => checkedKeys.has(code))).length;
};

export const isHighRiskPermission = (permission: PermissionViewNode): boolean => {
  return HIGH_RISK_SEGMENTS.has(getLastCodeSegment(permission.code));
};
