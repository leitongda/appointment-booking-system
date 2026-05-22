/**
 * 表单地址选点组件
 *
 * 封装"地址输入框 + 地图选点按钮 + Modal"的完整交互，
 * 支持 structured（拆分6字段）和 concatenated（拼接字符串）两种输出模式。
 *
 * 必须在 Form 或 ProForm 内部使用。
 *
 * @example
 * ```tsx
 * // 模式1：拼接字符串（适合只有 address 字段的场景）
 * <FormLocationPicker name="address" label="详细地址" mode="concatenated" />
 *
 * // 模式2：结构化字段（适合有省市区经纬度字段的场景）
 * <FormLocationPicker
 *   name="address"
 *   label="详细地址"
 *   mode="structured"
 *   fieldNames={{ province: 'province', city: 'city', district: 'district', longitude: 'longitude', latitude: 'latitude' }}
 * />
 * ```
 */
import React, { useState, useMemo } from 'react';
import { Form, Input, Button, Space } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';
import MapLocationPickerModal from '@/components/MapLocationPickerModal';
import type { LocationInfo } from '@/components/MapLocationPicker/types';
import { formatFullAddress, locationToFields } from '@/components/MapLocationPicker/types';

export interface FormLocationPickerProps {
  /** 表单字段名 */
  name: string;
  /** 标签文本 */
  label?: string;
  /** 输出模式：structured 拆分6字段，concatenated 拼接字符串 */
  mode?: 'structured' | 'concatenated';
  /** structured 模式下的子字段名映射 */
  fieldNames?: {
    province?: string;
    city?: string;
    district?: string;
    address?: string;
    longitude?: string;
    latitude?: string;
  };
  /** concatenated 模式下，是否包含省市区（默认 true） */
  includeRegion?: boolean;
  /** 按钮文本 */
  buttonText?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 地图弹窗标题 */
  modalTitle?: string;
  /** 输入框占位符 */
  placeholder?: string;
  /** 编辑模式下从表单已有值构造 LocationInfo */
  getInitialValue?: (formValues: any) => LocationInfo | undefined;
  /** 地图选点后额外回调 */
  onLocationChange?: (location: LocationInfo) => void;
}

const DEFAULT_FIELD_NAMES = {
  province: 'province',
  city: 'city',
  district: 'district',
  address: 'address',
  longitude: 'longitude',
  latitude: 'latitude',
};

const FormLocationPicker: React.FC<FormLocationPickerProps> = ({
  name,
  label,
  mode = 'concatenated',
  fieldNames = DEFAULT_FIELD_NAMES,
  includeRegion = true,
  buttonText = '地图选点',
  disabled = false,
  modalTitle = '选择地址',
  placeholder = '请选择地址',
  getInitialValue,
  onLocationChange,
}) => {
  const [mapModalVisible, setMapModalVisible] = useState(false);
  const form = Form.useFormInstance();

  const mergedFieldNames = useMemo(
    () => ({ ...DEFAULT_FIELD_NAMES, ...fieldNames }),
    [fieldNames],
  );

  const handleOk = (location: LocationInfo) => {
    if (mode === 'structured') {
      const fields = locationToFields(location);
      const values: Record<string, string> = {};
      values[mergedFieldNames.address!] = fields.address;
      values[mergedFieldNames.province!] = fields.province;
      values[mergedFieldNames.city!] = fields.city;
      values[mergedFieldNames.district!] = fields.district;
      values[mergedFieldNames.longitude!] = fields.longitude;
      values[mergedFieldNames.latitude!] = fields.latitude;
      form.setFieldsValue(values);
    } else {
      const value = includeRegion ? formatFullAddress(location) : location.address;
      form.setFieldsValue({ [name]: value || location.address });
    }

    onLocationChange?.(location);
    setMapModalVisible(false);
  };

  const handleButtonClick = () => {
    setMapModalVisible(true);
  };

  return (
    <>
      <Form.Item label={label} style={{ marginBottom: 0 }}>
        <Space.Compact style={{ width: '100%' }}>
          <Form.Item name={name} noStyle>
            <Input
              readOnly
              placeholder={placeholder}
              disabled={disabled}
              style={{ cursor: disabled ? 'not-allowed' : 'pointer' }}
              onClick={disabled ? undefined : handleButtonClick}
            />
          </Form.Item>
          <Button
            icon={<EnvironmentOutlined />}
            onClick={handleButtonClick}
            disabled={disabled}
          >
            {buttonText}
          </Button>
        </Space.Compact>
      </Form.Item>
      <MapLocationPickerModal
        open={mapModalVisible}
        onCancel={() => setMapModalVisible(false)}
        onOk={handleOk}
        initialValue={getInitialValue?.(form.getFieldsValue())}
        title={modalTitle}
      />
    </>
  );
};

export default FormLocationPicker;
