import React, { useEffect, useState } from 'react';
import { Modal } from 'antd';
import MapLocationPicker from '@/components/MapLocationPicker';
import type { LocationInfo } from '@/components/MapLocationPicker/types';

const MOBILE_BREAKPOINT = 768;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < MOBILE_BREAKPOINT : false
  );

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  return isMobile;
}

interface MapLocationPickerModalProps {
  /** 控制 Modal 显示（推荐） */
  open?: boolean;
  /** @deprecated 使用 open 代替 */
  visible?: boolean;
  onCancel: () => void;
  onOk: (location: LocationInfo) => void;
  initialValue?: LocationInfo;
  title?: string;
  width?: number;
  /** 地图高度，默认 400 */
  mapHeight?: number;
  /** 搜索框占位符 */
  placeholder?: string;
}

const MapLocationPickerModal: React.FC<MapLocationPickerModalProps> = ({
  open,
  visible,
  onCancel,
  onOk,
  initialValue,
  title = '选择地址',
  width = 720,
  mapHeight = 400,
  placeholder,
}) => {
  const isOpen = open ?? visible;
  const isMobile = useIsMobile();
  const [tempLocation, setTempLocation] = useState<LocationInfo | undefined>(initialValue);

  useEffect(() => {
    if (isOpen) {
      setTempLocation(initialValue);
    }
  }, [isOpen, initialValue]);

  const handleOk = () => {
    if (tempLocation?.address) {
      onOk(tempLocation);
    }
  };

  return (
    <Modal
      title={title}
      open={isOpen}
      onCancel={onCancel}
      onOk={handleOk}
      width={isMobile ? '100vw' : width}
      style={isMobile ? { top: 0, maxWidth: '100vw', padding: 0 } : undefined}
      styles={isMobile ? { body: { height: 'calc(100vh - 110px)', padding: '12px 16px' } } : undefined}
      destroyOnHidden
      okText="确定"
      cancelText="取消"
      okButtonProps={{ disabled: !tempLocation?.address }}
    >
      <MapLocationPicker
        value={tempLocation}
        onChange={setTempLocation}
        mapHeight={isMobile ? Math.min(mapHeight, 300) : mapHeight}
        placeholder={placeholder}
      />
    </Modal>
  );
};

export default MapLocationPickerModal;
