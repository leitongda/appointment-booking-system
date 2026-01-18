import React, { useState, useEffect } from 'react';
import { Modal, Space, Typography } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';
import AddressInput from '@/components/MapLocationPicker';
import type { LocationInfo } from '@/components/MapLocationPicker';

const { Text } = Typography;

interface AddressInputModalProps {
  visible: boolean;
  onCancel: () => void;
  onOk: (location: LocationInfo) => void;
  initialValue?: LocationInfo;
  title?: string;
  width?: number;
}

const AddressInputModal: React.FC<AddressInputModalProps> = ({
  visible,
  onCancel,
  onOk,
  initialValue,
  title = '输入地址',
  width = 600,
}) => {
  const [tempLocation, setTempLocation] = useState<LocationInfo | undefined>(initialValue);

  useEffect(() => {
    if (visible) {
      setTempLocation(initialValue);
    }
  }, [visible, initialValue]);

  const handleOk = () => {
    if (tempLocation?.address) {
      onOk(tempLocation);
    }
  };

  const handleLocationChange = (location: LocationInfo) => {
    setTempLocation(location);
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      onOk={handleOk}
      width={width}
      destroyOnClose={false}
      okText="确定"
      cancelText="取消"
      okButtonProps={{ disabled: !tempLocation?.address }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Text strong style={{ marginBottom: 8, display: 'block' }}>
            请输入完整的机构地址
          </Text>
          <AddressInput
            value={tempLocation}
            onChange={handleLocationChange}
            placeholder="例如：贵州省贵阳市观山湖区XXX中医馆"
          />
        </div>

        {tempLocation?.address && (
          <div style={{ padding: '12px 16px', background: '#f6f8fa', borderRadius: '6px' }}>
            <Space direction="vertical" size={4}>
              <div>
                <EnvironmentOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                <Text strong>地址预览：</Text>
              </div>
              <div style={{ paddingLeft: 22 }}>
                <Text>{tempLocation.address}</Text>
              </div>
            </Space>
          </div>
        )}
      </Space>
    </Modal>
  );
};

export default AddressInputModal;
