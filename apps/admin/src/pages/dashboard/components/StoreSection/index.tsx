import React, { useState, useEffect } from 'react';
import { QRCode, App, Spin, Empty } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { storeApi } from '@hospital/api';

interface CheckinQrcodeCardProps {
  storeId: string;
  storeName?: string;
}

const CheckinQrcodeCard: React.FC<CheckinQrcodeCardProps> = ({ storeId, storeName }) => {
  const { message } = App.useApp();
  const [qrcodeContent, setQrcodeContent] = useState('');
  const [qrcodeLoading, setQrcodeLoading] = useState(false);

  const { initialState } = useModel('@@initialState');
  const currentStore = initialState?.currentStore;

  useEffect(() => {
    if (storeId) {
      loadQrcode();
    }
  }, [storeId]);

  const loadQrcode = async () => {
    if (!storeId) return;
    setQrcodeLoading(true);
    try {
      const result = await storeApi.getCheckinQrcode(storeId);
      setQrcodeContent(result.qrcodeContent);
    } catch (error: any) {
      message.error(error.message || '获取二维码失败');
    } finally {
      setQrcodeLoading(false);
    }
  };

  const handleDownload = () => {
    const canvas = document.querySelector('#store-checkin-qrcode canvas') as HTMLCanvasElement;
    if (canvas) {
      const link = document.createElement('a');
      link.download = `签到二维码-${storeName || currentStore?.name || '门店'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  };

  return (
    <ProCard title="签到二维码" hoverable style={{ textAlign: 'center', padding: 16 }}>
      <Spin spinning={qrcodeLoading} tip="加载中..." />
      {qrcodeContent ? (
        <div id="store-checkin-qrcode">
          <QRCode
            value={qrcodeContent}
            size={200}
            style={{ margin: '0 auto' }}
          />
          <div style={{ marginTop: 16, color: '#666' }}>
            请使用微信扫描此二维码进行签到
          </div>
        </div>
      ) : (
        <Empty description="获取二维码失败" />
      )}
    </ProCard>
  );
};

export default CheckinQrcodeCard;
