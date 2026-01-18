import React, { useState } from 'react';
import { Input, Space, Typography } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface LocationInfo {
  address: string;
}

interface AddressInputProps {
  value?: LocationInfo;
  onChange?: (value: LocationInfo) => void;
  placeholder?: string;
}

const AddressInput: React.FC<AddressInputProps> = ({
  value,
  onChange,
  placeholder = '请输入完整地址，如：贵州省贵阳市观山湖区XXX中医馆',
}) => {
  const [address, setAddress] = useState(value?.address || '');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newAddress = e.target.value;
    setAddress(newAddress);
    onChange?.({ address: newAddress });
  };

  return (
    <div className="address-input">
      <Input
        placeholder={placeholder}
        prefix={<EnvironmentOutlined />}
        value={address}
        onChange={handleChange}
        allowClear
      />
      {address && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          <Space>
            <EnvironmentOutlined style={{ color: '#1890ff' }} />
            <Text type="secondary">已输入：{address}</Text>
          </Space>
        </div>
      )}
    </div>
  );
};

export default AddressInput;

