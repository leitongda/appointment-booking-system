import {
  QrcodeOutlined,
  MoneyCollectOutlined,
  ClockCircleOutlined,
  EditOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { history, useModel, useAccess } from '@umijs/max';
import { Tooltip, Dropdown, Modal, QRCode, Button, Spin, Empty, App, theme } from 'antd';
import type { MenuProps } from 'antd';
import { useState, useCallback } from 'react';
import { storeApi } from '@hospital/api';
import styles from './index.less';

export const StoreQuickActions: React.FC = () => {
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const { token } = theme.useToken();
  const access = useAccess();

  const [qrcodeModalVisible, setQrcodeModalVisible] = useState(false);
  const [qrcodeContent, setQrcodeContent] = useState('');
  const [qrcodeLoading, setQrcodeLoading] = useState(false);

  const currentStore = initialState?.currentStore;
  const isSuperAdmin = initialState?.currentUser?.isSuperAdmin || initialState?.currentUser?.roleCode === 'SUPER_ADMIN';

  const handleOpenQrcode = useCallback(async () => {
    if (!currentStore?.id) {
      message.warning('请先选择一个门店');
      return;
    }
    setQrcodeModalVisible(true);
    setQrcodeLoading(true);
    try {
      const result = await storeApi.getCheckinQrcode(currentStore.id);
      setQrcodeContent(result.qrcodeContent);
    } catch (error: any) {
      message.error(error.message || '获取二维码失败');
    } finally {
      setQrcodeLoading(false);
    }
  }, [currentStore?.id, message]);

  const handleDownloadQrcode = useCallback(() => {
    const canvas = document.querySelector('#store-header-qrcode canvas') as HTMLCanvasElement;
    if (canvas) {
      const link = document.createElement('a');
      link.download = `签到二维码-${currentStore?.name || '门店'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }, [currentStore?.name]);

  if (!currentStore || isSuperAdmin) {
    return null;
  }

  const menuItems: MenuProps['items'] = [
    {
      key: 'qrcode',
      icon: <QrcodeOutlined />,
      label: '签到二维码',
      onClick: handleOpenQrcode,
    },
    {
      key: 'fee',
      icon: <MoneyCollectOutlined />,
      label: '诊费设置',
      onClick: () => {
        history.push('/medical-services/consultation-fee/templates');
      },
    },
    {
      key: 'visit',
      icon: <ClockCircleOutlined />,
      label: '复诊规则',
      onClick: () => {
        history.push(`/organization/store/${currentStore?.id}/visit-type-config`);
      },
    },
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑门店',
      onClick: () => {
        history.push(`/organization/store/${currentStore?.id}/edit`);
      },
    },
  ].filter(item => {
    if (item.key === 'qrcode') return access.hasPermission('store:list');
    return access.hasPermission('store:update');
  });

  if (menuItems.length === 0) {
    return null;
  }

  return (
    <>
      <Dropdown menu={{ items: menuItems }} trigger={['click']} placement="bottomRight">
        <Tooltip title="门店管理">
          <div className={styles.actionItem}>
            <SettingOutlined />
          </div>
        </Tooltip>
      </Dropdown>

      <Modal
        title={`签到二维码 - ${currentStore?.name || ''}`}
        open={qrcodeModalVisible}
        onCancel={() => setQrcodeModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setQrcodeModalVisible(false)}>
            关闭
          </Button>,
          <Button key="download" type="primary" onClick={handleDownloadQrcode} disabled={!qrcodeContent}>
            下载二维码
          </Button>,
        ]}
        width={400}
        destroyOnHidden
      >
        <div style={{ textAlign: 'center', padding: '24px 0' }} id="store-header-qrcode">
          {qrcodeLoading ? (
            <Spin tip="加载中..." />
          ) : qrcodeContent ? (
            <>
              <QRCode
                value={qrcodeContent}
                size={256}
                style={{ margin: '0 auto' }}
              />
              <div style={{ marginTop: 16, color: token.colorTextSecondary }}>
                请使用微信扫描此二维码进行签到
              </div>
              <div style={{ marginTop: 8, fontSize: 12, color: token.colorTextTertiary }}>
                二维码内容: {qrcodeContent}
              </div>
            </>
          ) : (
            <Empty description="获取二维码失败" />
          )}
        </div>
      </Modal>
    </>
  );
};
