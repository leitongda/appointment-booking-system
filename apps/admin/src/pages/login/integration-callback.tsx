import { useEffect } from 'react';
import { Spin, Result } from 'antd';
import { history } from '@umijs/max';
import type { IntegrationLoginProvider } from '@hospital/api';

/**
 * 第三方平台 OAuth 扫码回调落地页。
 *
 * 平台扫码授权后会重定向到 redirect_uri（即本页），URL 携带 code 参数。
 * 本页提取 code 后写入 localStorage，登录页的 IntegrationLogin 组件
 * 通过轮询/storage 事件感知并完成登录态兑换。
 *
 * 路由：/login/integration-callback?provider=dingtalk&code=xxx&state=xxx
 */
const IntegrationCallbackPage: React.FC = () => {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const provider = params.get('provider') as IntegrationLoginProvider | null;
    const code = params.get('code');
    const state = params.get('state') || undefined;

    if (provider && code) {
      // 写入 localStorage 触发登录页组件感知
      localStorage.setItem(
        `integration_login_code_${provider}`,
        JSON.stringify({ code, state, ts: Date.now() }),
      );
      // 跳回登录页并切到对应 tab
      history.replace(`/login?loginType=${provider}`);
    } else {
      // 缺少参数，回到登录页
      history.replace('/login');
    }
  }, []);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Result
        icon={<Spin size="large" />}
        title="正在处理登录..."
        subTitle="请稍候，即将跳转回登录页"
      />
    </div>
  );
};

export default IntegrationCallbackPage;
