import { useState, useEffect, useCallback } from 'react';
import { MedicineBoxOutlined } from '@ant-design/icons';
import { App, Modal, Tabs } from 'antd';
import { history } from '@umijs/max';
import { setToken, STORAGE_KEYS, setStorage, getStorage, removeStorage, resetTokenExpiredState } from '@hospital/shared';
import { APP_TITLE } from '@config/appConfig';
import access from '@/access';
import { getDefaultRoute, isSafeReturnPath } from '@/utils/getDefaultRoute';
import { getSafeRouteMap } from '@/utils/deriveSafeRoutes';
import {
  AccountLogin, UserOutlined,
  PhoneLogin, MobileOutlined,
  WechatLogin, WechatOutlined,
  IntegrationLogin,
  IntegrationBindPhoneModal,
  type BindPhoneInfo,
} from './components';
import styles from './index.less';

type LoginType = 'wechat' | 'phone' | 'account' | 'dingtalk' | 'wecom' | 'feishu';

// 第三方集成登录平台元信息
const INTEGRATION_TABS: Array<{
  key: 'dingtalk' | 'wecom' | 'feishu';
  label: string;
  icon: React.ReactNode;
}> = [
  { key: 'dingtalk', label: '钉钉', icon: <MedicineBoxOutlined /> },
  { key: 'wecom', label: '企业微信', icon: <MedicineBoxOutlined /> },
  { key: 'feishu', label: '飞书', icon: <MedicineBoxOutlined /> },
];

const Login: React.FC = () => {
  const { message } = App.useApp();

  // 登录方式（从 localStorage 读取，实现刷新后保持选中状态）
  const [loginType, setLoginType] = useState<LoginType>(
    () => getStorage<LoginType>(STORAGE_KEYS.LOGIN_TYPE) || 'wechat'
  );

  // 延迟启用动画，避免初始化时的切换效果
  const [enableAnimation, setEnableAnimation] = useState(false);

  // 第三方登录绑定手机号弹窗
  const [bindPhoneOpen, setBindPhoneOpen] = useState(false);
  const [bindPhoneInfo, setBindPhoneInfo] = useState<BindPhoneInfo | null>(null);
  const [bindPhoneLabel, setBindPhoneLabel] = useState('');

  // 组件挂载后启用动画
  useEffect(() => {
    const timer = setTimeout(() => setEnableAnimation(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // 进入登录页时清理可能残留的"登录已过期"弹框。
  // 处理在上一页已弹出、跳转后才渲染到登录界面的竞态。
  useEffect(() => {
    Modal.destroyAll();
  }, []);

  // 登录成功后的处理
  const handleLoginSuccess = useCallback(async (result: any) => {
    // 重置 token 失效处理状态
    resetTokenExpiredState();
    
    setToken(result.accessToken);
    setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);

    // 保存租户 ID 到 localStorage，请求拦截器会自动将其添加到 X-Tenant-ID Header
    const tenantId = result.admin?.tenantId;
    if (tenantId) {
      setStorage(STORAGE_KEYS.CURRENT_TENANT_ID, tenantId);
    } else {
      removeStorage(STORAGE_KEYS.CURRENT_TENANT_ID);
    }
    
    // 保存门店信息到 localStorage
    // 支持单门店 (result.store) 和多门店 (result.stores) 场景
    let currentStore: any = null;
    if (result.stores && result.stores.length > 0) {
      // 多门店管理员，默认选择第一个门店
      currentStore = result.stores[0];
      setStorage(STORAGE_KEYS.CURRENT_STORE, currentStore);
    } else if (result.store) {
      // 兼容旧的单门店返回
      currentStore = result.store;
      setStorage(STORAGE_KEYS.CURRENT_STORE, currentStore);
    } else {
      // 超级管理员没有门店
      removeStorage(STORAGE_KEYS.CURRENT_STORE);
    }
    
    message.success('登录成功！');

    // 登录接口已经返回了用户信息，直接用于计算落地路由
    const currentUser = result.admin;

    // 获取上次访问的页面路径
    const lastPath = getStorage<string>(STORAGE_KEYS.LAST_PATH);
    // 清除存储的路径（只使用一次）
    removeStorage(STORAGE_KEYS.LAST_PATH);

    // 计算当前用户的 access 对象，用于决定安全的落地路由
    const accessMap = access({ currentUser: currentUser as any });

    // 默认落地路由：基于当前用户权限选出第一个可访问的叶子路由。
    // 避免硬编码 /dashboard —— 若用户无 dashboard 权限会陷入
    // 「/dashboard 无权限 → onUnAccessible 跳回 /dashboard」的死循环。
    const defaultPath = getDefaultRoute(accessMap);

    // lastPath 仅在用户对该路径有明确权限时才回跳，否则用默认路由。
    // 防止回跳到「上次因无权限被踢出的页面」或 redirect 跳板，避免死循环。
    const safeLastPath = lastPath && lastPath !== '/' && isSafeReturnPath(accessMap, lastPath)
      ? lastPath
      : defaultPath;

    // 诊断日志：当未回跳到原路径时，打印原因（是「路径不在安全集合」还是「无权限」），
    // 便于今后定位任何路由漏配边缘情况。安全集合由路由树自动派生（见 deriveSafeRoutes）。
    if (lastPath && lastPath !== '/' && lastPath !== safeLastPath) {
      const lastPathname = lastPath.split(/[?#]/)[0];
      const safeMap = getSafeRouteMap();
      const accessKey = safeMap.get(lastPathname);
      // accessMap 用宽松索引类型读取，与 getDefaultRoute/isSafeReturnPath 内部一致。
      const accessMapLoose = accessMap as Record<string, unknown>;
      const reason = !accessKey
        ? 'path not a safe leaf route (redirect/详情页/表单页/layout:false)'
        : !accessMapLoose[accessKey]
          ? `no permission (requires ${accessKey})`
          : 'unknown';
      console.log('[login-redirect] 丢弃 lastPath，原因：', reason);
    }
    console.log('[login-redirect] lastPath =', lastPath, '| safeLastPath =', safeLastPath);

    // 使用整页跳转而非 SPA history.push。
    //
    // 原实现 setInitialState + setTimeout(history.push) 存在时序竞态：
    // 扫码登录/集成登录等通过轮询（setInterval/storage 事件）触发，属于
    // 非 React 事件上下文，React 18 不会同步刷新 setInitialState 的状态更新。
    // 当 setTimeout(0) 的宏任务执行 history.push 时，ProLayout 的 access 检查
    // 可能仍读到旧的 currentUser=undefined → 渲染 403 → 跳到默认页，导致
    // 「登录后不回到原界面」。
    //
    // 整页跳转会让 getInitialState 重新执行并加载完整用户信息，access 基于
    // 完整权限计算，彻底消除竞态。登录是一次性操作，整页刷新体验可接受。
    setTimeout(() => {
      window.location.href = safeLastPath;
    }, 0);
  }, [message]);

  const tabItems = [
    {
      key: 'wechat',
      label: (
        <span>
          <WechatOutlined />
          微信登录
        </span>
      ),
      children: <WechatLogin onSuccess={handleLoginSuccess} />,
    },
    {
      key: 'phone',
      label: (
        <span>
          <MobileOutlined />
          验证码登录
        </span>
      ),
      children: <PhoneLogin onSuccess={handleLoginSuccess} />,
    },
    {
      key: 'account',
      label: (
        <span>
          <UserOutlined />
          账号登录
        </span>
      ),
      children: <AccountLogin onSuccess={handleLoginSuccess} />,
    },
    ...INTEGRATION_TABS.map((tab) => ({
      key: tab.key,
      label: (
        <span>
          {tab.icon}
          {tab.label}登录
        </span>
      ),
      children: (
        <IntegrationLogin
          provider={tab.key}
          label={tab.label}
          icon={tab.icon}
          onSuccess={handleLoginSuccess}
          onNeedBindPhone={(info) => {
            setBindPhoneInfo(info);
            setBindPhoneLabel(tab.label);
            setBindPhoneOpen(true);
          }}
        />
      ),
    })),
  ];

  return (
    <div className={styles.container}>
      <div className={styles.background} />
      <div className={styles.content}>
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.logo}><MedicineBoxOutlined /></div>
            <h1 className={styles.title}>{APP_TITLE}</h1>
          </div>
          
          <Tabs
            activeKey={loginType}
            onChange={(key) => {
              const newType = key as LoginType;
              setLoginType(newType);
              setStorage(STORAGE_KEYS.LOGIN_TYPE, newType);
            }}
            items={tabItems.map(item => ({ ...item, destroyOnHidden: true }))}
            centered
            className={styles.loginTabs}
            animated={enableAnimation}
          />
        </div>
      </div>
      <div className={styles.footer}>
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
        >
          蜀ICP备2022022726号-2
        </a>
      </div>
      <IntegrationBindPhoneModal
        open={bindPhoneOpen}
        info={bindPhoneInfo}
        label={bindPhoneLabel}
        onSuccess={(result) => {
          setBindPhoneOpen(false);
          handleLoginSuccess(result);
        }}
        onCancel={() => setBindPhoneOpen(false)}
      />
    </div>
  );
};

export default Login;
