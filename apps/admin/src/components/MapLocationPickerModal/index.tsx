import React, { useState, useEffect } from 'react';
import { Modal, Alert, Space, Typography } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';
import MapLocationPicker from '@/components/MapLocationPicker';
import type { LocationInfo } from '@/components/MapLocationPicker';
import './index.less';

const { Text } = Typography;

interface MapLocationPickerModalProps {
  visible: boolean;
  onCancel: () => void;
  onOk: (location: LocationInfo) => void;
  initialValue?: LocationInfo;
  title?: string;
  width?: number;
}

const MapLocationPickerModal: React.FC<MapLocationPickerModalProps> = ({
  visible,
  onCancel,
  onOk,
  initialValue,
  title = '选择位置',
  width = 900,
}) => {
  const [tempLocation, setTempLocation] = useState<LocationInfo | undefined>(initialValue);

  useEffect(() => {
    if (visible) {
      setTempLocation(initialValue);
    }
  }, [visible, initialValue]);

  const handleOk = () => {
    if (tempLocation) {
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
      destroyOnClose
      okText="确定"
      cancelText="取消"
      okButtonProps={{ disabled: !tempLocation?.longitude || !tempLocation?.latitude }}
    >
      <MapLocationPicker
        value={tempLocation}
        onChange={handleLocationChange}
        height={500}
        placeholder="搜索地址，如：xxx中医馆"
      />

      {tempLocation && (
        <Alert
          message={
            <Space direction="vertical" size={4}>
              <div>
                <EnvironmentOutlined style={{ marginRight: 8 }} />
                <Text strong>已选择位置：</Text>
                <Text>{tempLocation.formattedAddress || tempLocation.address || '未知地址'}</Text>
              </div>
              <div style={{ paddingLeft: 22 }}>
                <Text type="secondary">
                  经度: {tempLocation.longitude} | 纬度: {tempLocation.latitude}
                </Text>
              </div>
            </Space>
          }
          type="info"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}
    </Modal>
  );
};

export default MapLocationPickerModal;
