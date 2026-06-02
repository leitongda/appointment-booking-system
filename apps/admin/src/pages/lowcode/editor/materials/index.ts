/** 物料注册表 */

import type { MaterialComponent } from '@hospital/shared';
import { basicMaterials } from './basic';
import { layoutMaterials } from './layout';
import { displayMaterials } from './display';
import { formMaterials } from './form';

/** 所有物料组件 */
export const allMaterials: MaterialComponent[] = [
  ...basicMaterials,
  ...layoutMaterials,
  ...displayMaterials,
  ...formMaterials,
];

/** 按分类分组的物料 */
export const materialsByCategory = {
  basic: basicMaterials,
  layout: layoutMaterials,
  display: displayMaterials,
  form: formMaterials,
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
