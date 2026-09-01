/** 物料注册表 */

import type { MaterialComponent } from '@hospital/shared';
import { basicMaterials } from './basic';
import { layoutMaterials } from './layout';
import { displayMaterials } from './display';
import { formMaterials } from './form';
import { businessMaterials } from './business';

/** 所有物料组件 */
export const allMaterials: MaterialComponent[] = [
  ...basicMaterials,
  ...layoutMaterials,
  ...displayMaterials,
  ...formMaterials,
  ...businessMaterials,
];

/** 按分类分组的物料 */
export const materialsByCategory = {
  basic: basicMaterials,
  layout: layoutMaterials,
  display: displayMaterials,
  form: formMaterials,
  business: businessMaterials,
} as const;

/** 分类显示名称 */
export const categoryLabels: Record<string, string> = {
  basic: '基础',
  layout: '布局',
  display: '展示',
  form: '表单',
  business: '业务',
};

/** 根据 componentName 查找物料定义 */
export function findMaterial(
  componentName: string,
): MaterialComponent | undefined {
  return allMaterials.find((m) => m.componentName === componentName);
}

/**
 * 展示层分组 — 对齐目标线框图的左栏分类（列表类/布局类/基础组件/交互类/媒体类）。
 *
 * 注意：底层 category 字段（basic/layout/display/form/business）保持不变，
 * 以避免触及共享类型联合类型与 codegen 依赖。此处仅做展示层映射。
 * key 顺序即展示顺序。
 */
export interface DisplayGroup {
  key: string;
  label: string;
  materials: MaterialComponent[];
}

/** 按 componentName 归入展示分组的映射表 */
const COMPONENT_DISPLAY_GROUP: Record<string, string> = {
  // 列表类
  NutCell: 'list',
  NutCard: 'list',
  NutTabs: 'list',
  // 布局类
  NutView: 'layout',
  NutRow: 'layout',
  NutCol: 'layout',
  NutSearchBar: 'layout',
  NutNavBar: 'layout',
  // 基础组件
  NutText: 'basic',
  NutImage: 'basic',
  NutButton: 'basic',
  NutDivider: 'basic',
  NutIcon: 'basic',
  NutTag: 'basic',
  NutAvatar: 'basic',
  NutBadge: 'basic',
  NutEmpty: 'basic',
  // 媒体类
  NutSwiper: 'media',
  NutSwiperItem: 'media',
  NutProgress: 'media',
};

/**
 * 不应在左栏独立展示的组件（由父组件统一渲染，独立拖入无意义）。
 * - NutTabPane：由父 NutTabs 渲染（SchemaRenderer 中 case 直接 return null）
 */
const HIDDEN_FROM_PALETTE = new Set<string>(['NutTabPane']);

/** 展示分组标签（顺序即左栏展示顺序） */
const DISPLAY_GROUP_LABELS: { key: string; label: string }[] = [
  { key: 'list', label: '列表类' },
  { key: 'layout', label: '布局类' },
  { key: 'basic', label: '基础组件' },
  { key: 'interactive', label: '交互类' },
  { key: 'media', label: '媒体类' },
];

/** 构建展示分组（基于 componentName 映射；未显式映射的归入「交互类」） */
export const displayGroups: DisplayGroup[] = DISPLAY_GROUP_LABELS.map(
  ({ key, label }) => ({
    key,
    label,
    materials: allMaterials.filter((m) => {
      if (HIDDEN_FROM_PALETTE.has(m.componentName)) return false;
      const group = COMPONENT_DISPLAY_GROUP[m.componentName] ?? 'interactive';
      return group === key;
    }),
  }),
).filter((g) => g.materials.length > 0);
