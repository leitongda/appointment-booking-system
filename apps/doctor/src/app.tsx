import { message, Dropdown, Avatar, Space } from 'antd';
import type { RequestConfig, RunTimeLayoutConfig } from 'umi';
import { history } from 'umi';
import { getToken, removeToken } from '@hospital/shared';
import { userApi, doctorApi, setBaseURL } from '@hospital/api';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import { initApiConfig } from '@/utils/request';

// 设置 API 基础路径（从环境变量读取，支持动态配置）
const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';
setBaseURL(apiBaseUrl);

// 初始化 API 请求配置（拦截器）
initApiConfig();

interface CurrentUser {
  id: string;
  phone: string;
  nickname?: string;
  avatar?: string;
  doctorId?: string;
  doctorName?: string;
  departmentName?: string;
}

export async function getInitialState(): Promise<{ currentUser?: CurrentUser }> {
  const token = getToken();
  if (!token) {
    return {};
  }
  
  // 登录页不需要获取用户信息
  if (history.location.pathname === '/login') {
    return {};
  }
  
  try {
    const user = await userApi.getProfile();
    // 医生端需要获取医生信息
    // 假设医生登录后，可以通过某种方式获取关联的医生信息
    return { 
      currentUser: {
        id: user.id,
        phone: user.phone,
        nickname: user.nickname,
        avatar: user.avatar,
      }
    };
  } catch (error) {
    removeToken();
    return {};
  }
}

export const layout: RunTimeLayoutConfig = ({ initialState, setInitialState }) => {
  const handleLogout = () => {
    removeToken();
    setInitialState({ currentUser: undefined });
    history.push('/login');
    message.success('已退出登录');
  };

  return {
    logo: '/logo.svg',
    title: '医生工作站',
    menu: { locale: false },
    rightContentRender: () => {
      if (!initialState?.currentUser) {
        return null;
      }

      const menuItems = [
        {
          key: 'settings',
          icon: <SettingOutlined />,
          label: '个人设置',
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
            <span>{initialState.currentUser.nickname || initialState.currentUser.phone}</span>
          </Space>
        </Dropdown>
      );
    },
    onPageChange: () => {
      if (!initialState?.currentUser && location.pathname !== '/login') {
        history.push('/login');
      }
    },
  };
};

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
        config.headers = { ...config.headers, Authorization: `Bearer ${token}` };
      }
      return config;
    },
  ],
  responseInterceptors: [
    (response: any) => {
      const { data, status } = response;
      
      if (status === 401 || data?.code === 401) {
        removeToken();
        history.push('/login');
        return response;
      }
      
      if (data?.code && data.code !== 200 && data.code !== 0) {
        message.error(data?.message || '请求失败');
      }
      
      return response;
    },
  ],
};
