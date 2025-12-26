import { useState, useEffect, useRef, useCallback } from 'react';
import { WechatOutlined } from '@ant-design/icons';
import { App, QRCode, Spin } from 'antd';
import { adminApi } from '@hospital/api';
import styles from './index.less';

interface WechatLoginProps {
  onSuccess: (result: any) => void;
}

const WechatLogin: React.FC<WechatLoginProps> = ({ onSuccess }) => {
  const { message } = App.useApp();
  
  const [qrcodeUrl, setQrcodeUrl] = useState('');
  const [qrcodeTicket, setQrcodeTicket] = useState('');
  const [qrcodeStatus, setQrcodeStatus] = useState<'loading' | 'active' | 'expired'>('loading');
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 获取微信二维码
  const fetchWechatQrcode = useCallback(async () => {
    setQrcodeStatus('loading');
    try {
      const result = await adminApi.getWechatQrcode();
      setQrcodeUrl(result.qrcodeUrl);
      setQrcodeTicket(result.ticket);
      setQrcodeStatus('active');
    } catch (error: any) {
      message.error('获取二维码失败');
      setQrcodeStatus('expired');
    }
  }, [message]);

  // 轮询检查扫码状态
  const pollWechatStatus = useCallback(async () => {
    if (!qrcodeTicket || qrcodeStatus !== 'active') return;
    
    try {
      const result = await adminApi.checkWechatScan(qrcodeTicket);
      
      if (result.status === 'confirmed' && result.accessToken) {
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        onSuccess(result);
      } else if (result.status === 'expired') {
        setQrcodeStatus('expired');
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      }
    } catch (error) {
      // 忽略轮询错误
    }
  }, [qrcodeTicket, qrcodeStatus, onSuccess]);

  // 组件挂载时获取二维码
  useEffect(() => {
    fetchWechatQrcode();
    
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [fetchWechatQrcode]);

  // 开始轮询
  useEffect(() => {
    if (qrcodeStatus === 'active' && qrcodeTicket) {
      pollTimerRef.current = setInterval(pollWechatStatus, 2000);
    }
    
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [qrcodeStatus, qrcodeTicket, pollWechatStatus]);

  return (
    <div className={styles.wechatLogin}>
      <div className={styles.qrcodeWrapper}>
        {qrcodeStatus === 'loading' && (
          <div className={styles.qrcodeLoading}>
            <Spin size="large" />
            <p>加载中...</p>
          </div>
        )}
        {qrcodeStatus === 'active' && (
          <>
            <QRCode 
              value={qrcodeUrl || '-'} 
              size={180}
              status="active"
              bordered={false}
            />
            <p className={styles.qrcodeTip}>请使用微信扫描二维码登录</p>
          </>
        )}
        {qrcodeStatus === 'expired' && (
          <div className={styles.qrcodeExpired}>
            <QRCode 
              value="-" 
              size={180}
              status="expired"
              bordered={false}
              onRefresh={fetchWechatQrcode}
            />
            <p>二维码已过期，请刷新</p>
          </div>
        )}
      </div>
    </div>
  );
};

export { WechatLogin, WechatOutlined };
export default WechatLogin;
