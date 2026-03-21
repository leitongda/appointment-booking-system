/**
 * PC端地区选择器组件
 * 基于 ProFormCascader 封装，支持省市区三级联动
 */

import React from 'react';
import { ProFormCascader } from '@ant-design/pro-components';
import regionsData from '../../data/regions.json';
import type { RegionOption, RegionCode } from '../../types/region';

type ProFormCascaderProps = React.ComponentProps<typeof ProFormCascader>;

/**
 * 地区选择器组件属性
 */
export interface RegionSelectorProps extends Omit<ProFormCascaderProps, 'fieldProps'> {
  /** 字段属性 */
  fieldProps?: ProFormCascaderProps['fieldProps'];
  /** 是否显示搜索框 */
  showSearch?: boolean;
  /** 占位符 */
  placeholder?: string;
}

/**
 * ProForm 地区选择器组件
 *
 * @example
 * ```tsx
 * // 基本使用
 * <ProFormRegionSelector
 *   name="region"
 *   label="所在地区"
 *   rules={[{ required: true, message: '请选择所在地区' }]}
 * />
 *
 * // 使用 transform 转换为独立字段
 * <ProFormRegionSelector
 *   name="region"
 *   label="所在地区"
 *   transform={(value) => ({
 *     province: value?.[0],
 *     city: value?.[1],
 *     district: value?.[2],
 *   })}
 * />
 * ```
 */
export const ProFormRegionSelector: React.FC<RegionSelectorProps> = ({
  showSearch = true,
  placeholder = '请选择省/市/区',
  fieldProps,
  ...props
}) => {
  return (
    <ProFormCascader
      fieldProps={{
        options: regionsData as RegionOption[],
        showSearch: showSearch,
        placeholder: placeholder,
        changeOnSelect: true, // 允许选择任意一级
        ...fieldProps,
      }}
      {...props}
    />
  );
};

/**
 * 默认导出
 */
export default ProFormRegionSelector;

/**
 * 导出地区数据，供其他组件使用
 */
export { regionsData };
export type { RegionOption, RegionCode };
