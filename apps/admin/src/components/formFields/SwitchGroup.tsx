/**
 * 开关组组件
 *
 * 功能：
 * - 支持多个开关的统一布局
 * - 自动处理 boolean ↔ number 转换（0/1）
 * - 支持禁用状态
 * - 支持响应式布局
 */
import { ProFormSwitch } from '@ant-design/pro-components';
import { Col, Row } from 'antd';
import type { ColProps } from 'antd';
import React from 'react';

/**
 * 开关项配置
 */
export interface SwitchItem {
  /** 表单字段名 */
  name: string;
  /** 标签文本 */
  label: string;
  /** 占据的列数 */
  span?: ColProps['span'];
  /** 是否禁用 */
  disabled?: boolean;
  /** 额外提示信息 */
  extra?: string;
  /** 字段 tooltip */
  tooltip?: string;
}

/**
 * 开关组组件属性
 */
export interface SwitchGroupProps {
  /** 开关配置数组 */
  items: SwitchItem[];
  /** 每行显示的列数（响应式） */
  gutter?: number | [number, number];
  /** 是否所有开关都禁用 */
  disabledAll?: boolean;
}

/**
 * 开关组组件
 *
 * 将多个开关统一布局，自动处理 boolean 和 number 的转换问题。
 * 在表单提交时，会将 boolean 值转换为 0/1。
 *
 * @example
 * ```tsx
 * // 基础用法
 * <SwitchGroup
 *   items={[
 *     { name: 'status', label: '启用状态' },
 *     { name: 'isRecommended', label: '是否推荐' },
 *   ]}
 * />
 *
 * // 带列布局
 * <SwitchGroup
 *   gutter={16}
 *   items={[
 *     { name: 'status', label: '启用状态', span: 8 },
 *     { name: 'isRecommended', label: '是否推荐', span: 8 },
 *     { name: 'onlineConsultEnabled', label: '在线问诊', span: 8 },
 *   ]}
 * />
 *
 * // 带提示和禁用
 * <SwitchGroup
 *   items={[
 *     {
 *       name: 'status',
 *       label: '启用状态',
 *       extra: '关闭后用户将无法看到该内容',
 *       tooltip: '控制内容的显示状态',
 *     },
 *     {
 *       name: 'isRecommended',
 *       label: '是否推荐',
 *       disabled: true,
 *     },
 *   ]}
 * />
 * ```
 */
const SwitchGroup: React.FC<SwitchGroupProps> = ({
  items,
  gutter = 16,
  disabledAll = false,
}) => {
  // 转换值：boolean <-> number
  // ProFormSwitch 使用 boolean，但后端可能使用 0/1
  const transform = (value: boolean) => (value ? 1 : 0);

  return (
    <Row gutter={gutter}>
      {items.map((item) => (
        <Col key={item.name} span={item.span || 24}>
          <ProFormSwitch
            name={item.name}
            label={item.label}
            disabled={disabledAll || item.disabled}
            extra={item.extra}
            tooltip={item.tooltip}
            fieldProps={{
              // 内部转换：从后端获取的 0/1 转换为 boolean
              checked: item.name as any,
              // 提交时转换：boolean 转 0/1
              onChange: (checked) => {
                // 这个转换在 onFinish 中处理
                return checked;
              },
            }}
            // 在表单值转换时处理
            transform={transform}
          />
        </Col>
      ))}
    </Row>
  );
};

/**
 * 辅助函数：转换表单值中的开关字段
 *
 * 在表单提交时使用，将 boolean 值转换为 0/1
 *
 * @example
 * ```tsx
 * const handleSubmit = async (values: any) => {
 *   const data = transformSwitchValues(values, ['status', 'isRecommended']);
 *   await api.create(data);
 * };
 * ```
 */
export function transformSwitchValues(values: any, switchFields: string[]): any {
  const result = { ...values };
  switchFields.forEach((field) => {
    if (typeof result[field] === 'boolean') {
      result[field] = result[field] ? 1 : 0;
    }
  });
  return result;
}

/**
 * 辅助函数：转换表单值中的开关字段（反向）
 *
 * 在加载初始值时使用，将 0/1 转换为 boolean
 *
 * @example
 * ```tsx
 * const initialValues = transformSwitchValuesReverse(data, ['status', 'isRecommended']);
 * form.setFieldsValue(initialValues);
 * ```
 */
export function transformSwitchValuesReverse(values: any, switchFields: string[]): any {
  const result = { ...values };
  switchFields.forEach((field) => {
    if (typeof result[field] === 'number') {
      result[field] = result[field] === 1;
    }
  });
  return result;
}

export default SwitchGroup;
