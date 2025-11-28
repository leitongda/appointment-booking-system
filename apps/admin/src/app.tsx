import { message, Dropdown, Avatar, Space } from 'antd';
import type { RequestConfig, RunTimeLayoutConfig } from 'umi';
import { history } from 'umi';
import { getToken, removeToken, setToken } from '@hospital/shared';
import { adminApi } from '@hospital/api';
import type { Admin } from '@hospital/api';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';

/**
 * 初始化状态
 */
export async function getInitialState(): Promise<{
  currentUser?: Admin;
}> {
  const token = getToken();
  if (!token) {
    return {};
  }
  
  // 登录页不需要获取用户信息
  if (history.location.pathname === '/login') {
    return {};
  }
  
  try {
    const currentUser = await adminApi.getCurrentAdmin();
    return { currentUser };
  } catch (error) {
    // token 无效，清除并跳转登录
    removeToken();
    return {};
  }
}

/**
 * Layout 配置
 */
export const layout: RunTimeLayoutConfig = ({ initialState, setInitialState }) => {
  const handleLogout = () => {
    removeToken();
    setInitialState({ currentUser: undefined });
    history.push('/login');
    message.success('已退出登录');
  };

  return {
    logo: '/logo.svg',
    title: '医院管理后台',
    menu: {
      locale: false,
    },
    rightContentRender: () => {
      if (!initialState?.currentUser) {
        return null;
      }
      
      const menuItems = [
        {
          key: 'settings',
          icon: <SettingOutlined />,
          label: '个人设置',
          onClick: () => history.push('/system/settings'),
        },
        {
          type: 'divider' as const,
        },
        {
          key: 'logout',
          icon: <LogoutOutlined />,
          label: '退出登录',
          onClick: handleLogout,
        },
      ];

      return (
        <Dropdown menu={{ items: menuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer', padding: '0 12px' }}>
            <Avatar 
              size="small" 
              icon={<UserOutlined />} 
              src={initialState.currentUser.avatar}
            />
            <span>{initialState.currentUser.name || initialState.currentUser.username}</span>
          </Space>
        </Dropdown>
      );
    },
    onPageChange: () => {
      const { location } = history;
      // 如果没有登录，重定向到登录页
      if (!initialState?.currentUser && location.pathname !== '/login') {
        history.push('/login');
      }
    },
    // 自定义 403 页面
    unAccessible: <div>无权限访问</div>,
  };
};

/**
 * Request 配置
 */
export const request: RequestConfig = {
  timeout: 30000,
  errorConfig: {
    errorHandler: (error: any) => {
      if (error.response?.status !== 401) {
        message.error(error.message || '请求失败');
      }
    },
  },
  requestInterceptors: [
    (config: any) => {
      const token = getToken();
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        };
      }
      return config;
    },
  ],
  responseInterceptors: [
    (response: any) => {
      const { data, status } = response;
      
      // 401 未授权
      if (status === 401 || data?.code === 401) {
        removeToken();
        history.push('/login');
        return response;
      }
      
      // 业务错误
      if (data?.code && data.code !== 200 && data.code !== 0) {
        message.error(data?.message || '请求失败');
      }
      
      return response;
    },
  ],
};
