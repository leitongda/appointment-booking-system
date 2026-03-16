import React, { useState, from 'react';
import { QRCode, Button, message, App, from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { storeApi } from '@hospital/api';

interface CheckinQrcodeCardProps {
  storeId: string;
  storeName?: string;
}

const CheckinQrcodeCard: React.FC<CheckinQrcodeCardProps> {
  const { message } = App.useApp();
  const [qrcodeContent, setQrcodeContent] = useState('');
  const [qrcodeLoading, setQrcodeLoading] = useState(false);

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
    } catch (error) {
      message.error('获取二维码失败');
    } finally {
      setQrcodeLoading(false);
    }
  };

  const handleDownloadQrcode = () => {
    const canvas = document.querySelector('#store-checkin-qrcode canvas') as HTMLCanvasElement;
    if (canvas) {
      const link = document.createElement('a');
      link.download = `签到二维码-${storeName || '门店'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  };

  return (
    <ProCard
      title="签到二维码"
      hoverable
      style={{ textAlign: 'center', padding: 16 }}
    >
      <Spin spinning={qrcodeLoading} tip="加载中..." />
      {qrcodeContent ? (
        <>
          <QRCode
            id="store-checkin-qrcode"
            value={qrcodeContent}
            size={200}
            style={{ margin: '0 auto' }}
          />
          <div style={{ marginTop: 16, color: '#666' }}>
            请使用微信扫描此二维码进行签到
          </div>
          <Button type="primary" onClick={handleDownloadQrcode}>
            下载二维码
          </Button>
        </>
      ) : (
        <Empty description="获取二维码失败" />
      )}
    </ProCard>
  );
};

export default CheckinQrcodeCard;
