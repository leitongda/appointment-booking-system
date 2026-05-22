/**
 * 表单字段组件统一导出
 *
 * @example
 * ```tsx
 * import { PasswordField, SwitchGroup, ImageUploadCard, FormLocationPicker } from '@/components/formFields';
 * ```
 */

export { default as PasswordField } from './PasswordField';
export type { PasswordFieldProps, PasswordStrengthLevel } from './PasswordField';

export { default as SwitchGroup, transformSwitchValues, transformSwitchValuesReverse } from './SwitchGroup';
export type { SwitchGroupProps, SwitchItem } from './SwitchGroup';

export { default as ImageUploadCard } from './ImageUploadCard';
export type { ImageUploadCardProps } from './ImageUploadCard';

export { default as FormLocationPicker } from './FormLocationPicker';
export type { FormLocationPickerProps } from './FormLocationPicker';
