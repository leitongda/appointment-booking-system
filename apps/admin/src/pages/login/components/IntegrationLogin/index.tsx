import { useState, useEffect, useRef, useCallback } from 'react';
import { App, QRCode, Spin, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { adminApi, type IntegrationLoginProvider } from '@hospital/api';
import styles from './index.less';

export interface IntegrationLoginProps {
  provider: IntegrationLoginProvider;
  label: string; // 平台中文名
  icon?: React.ReactNode;
  onSuccess: (result: any) => void;
  onNeedBindPhone?: (info: {
    provider: IntegrationLoginProvider;
    externalId?: string;
    unionId?: string;
    name?: string;
  }) => void;
}

/**
 * 第三方平台扫码登录通用组件（钉钉/企业微信/飞书）。
 *
 * 流程：
 * 1. 调用 getIntegrationQrcode 获取平台扫码授权 URL（含 state）
 * 2. 用 antd QRCode 渲染授权 URL（用户用平台 App 扫码）
 * 3. 用户扫码授权后，平台回调到 redirect_uri（回调页 /login/integration-callback）
 * 4. 回调页拿到 code 后调用 integrationLogin 换取登录态
 *
 * 注：扫码授权在平台侧完成后会跳转，本组件仅负责展示二维码。
 * 回调处理见 IntegrationCallbackPage。
 */
const IntegrationLogin: React.FC<IntegrationLoginProps> = ({
  provider,
  label,
  icon,
  onSuccess,
  onNeedBindPhone,
}) => {
  const { message } = App.useApp();
  const [qrcodeUrl, setQrcodeUrl] = useState('');
  const [status, setStatus] = useState<'loading' | 'active' | 'expired'>('loading');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const doneRef = useRef(false); // 标记登录流程已结束，停止轮询

  // 构造回调地址（当前站点 + 回调路由）
  const buildRedirectUri = useCallback(() => {
    const base = window.location.origin;
    return `${base}/login/integration-callback?provider=${provider}`;
  }, [provider]);

  const fetchQrcode = useCallback(async () => {
    setStatus('loading');
    doneRef.current = false; // 重置，允许新一轮扫码
    try {
      const result = await adminApi.getIntegrationQrcode(provider, buildRedirectUri());
      setQrcodeUrl(result.qrcodeUrl);
      setStatus('active');
    } catch (error: any) {
      message.error(error?.message || `获取${label}二维码失败`);
      setStatus('expired');
    }
  }, [provider, label, buildRedirectUri, message]);

  const handleCode = useCallback(
    async (code: string, state?: string) => {
      if (doneRef.current) return; // 已处理过，避免重复调用
      doneRef.current = true;
      // 停止轮询
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      try {
        const result = await adminApi.integrationLogin(provider, code, state);
        if (result.needBindPhone) {
          // 未绑定本地账号，引导绑定手机号
          onNeedBindPhone?.({
            provider,
            externalId: result.externalId,
            unionId: result.unionId,
            name: result.name,
          });
        } else if (result.accessToken) {
          onSuccess(result);
        } else {
          message.error('登录失败，请重试');
          setStatus('expired');
          doneRef.current = false; // 允许重试
        }
      } catch (error: any) {
        message.error(error?.message || `${label}登录失败`);
        setStatus('expired');
        doneRef.current = false; // 出错允许重试
      }
    },
    [provider, label, onSuccess, onNeedBindPhone, message],
  );

  useEffect(() => {
    fetchQrcode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 监听 localStorage 事件：回调页拿到 code 后会写入并触发本组件完成登录
  useEffect(() => {
    const storageKey = `integration_login_code_${provider}`;
    const handleStorage = (e: StorageEvent) => {
      if (doneRef.current) return;
      if (e.key === storageKey && e.newValue) {
        const payload = JSON.parse(e.newValue);
        localStorage.removeItem(storageKey);
        handleCode(payload.code, payload.state);
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider]);

  // 同时轮询检测同一 tab 内的回调（storage 事件不在同 tab 触发）
  useEffect(() => {
    const storageKey = `integration_login_code_${provider}`;
    pollingRef.current = setInterval(() => {
      if (doneRef.current) return;
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        try {
          const payload = JSON.parse(raw);
          localStorage.removeItem(storageKey);
          handleCode(payload.code, payload.state);
        } catch {
          /* ignore */
        }
      }
    }, 1000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider]);


  return (
    <div className={styles.wechatLogin}>
      <div className={styles.qrcodeWrapper}>
        {status === 'loading' && (
          <div className={styles.qrcodeLoading}>
            <Spin size="large" />
            <p>加载中...</p>
          </div>
        )}
        {status === 'active' && (
          <>
            <QRCode value={qrcodeUrl || '-'} size={180} status="active" bordered={false} />
            <p className={styles.qrcodeTip}>
              {icon} 请使用{label}扫描二维码登录
            </p>
          </>
        )}
        {status === 'expired' && (
          <div className={styles.qrcodeExpired}>
            <Button icon={<ReloadOutlined />} onClick={fetchQrcode}>
              重新获取二维码
            </Button>
            <p>二维码已失效，请刷新</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntegrationLogin;
