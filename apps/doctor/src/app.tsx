import { message, Dropdown, Avatar, Space } from 'antd';
import type { RequestConfig, RunTimeLayoutConfig } from 'umi';
import { history } from 'umi';
import { getToken, removeToken } from '@hospital/shared';
import { doctorApi, setBaseURL } from '@hospital/api';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import { initApiConfig } from '@/utils/request';

// 设置 API 基础路径（从环境变量读取，支持动态配置）
const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';
setBaseURL(apiBaseUrl);

// 初始化 API 请求配置（拦截器）
initApiConfig();

interface CurrentDoctor {
  id: string;
  name: string;
  phone?: string;
  avatar?: string;
  title?: string;
  departmentId?: string;
  departmentName?: string;
  storeId?: string;
  storeName?: string;
}

export async function getInitialState(): Promise<{ currentDoctor?: CurrentDoctor }> {
  const token = getToken();
  if (!token) {
    return {};
  }
  
  // 登录页不需要获取用户信息
  if (history.location.pathname === '/login') {
    return {};
  }
  
  try {
    // 使用医生专用 API 获取当前登录医生信息
    const doctor = await doctorApi.getMe();
    return { 
      currentDoctor: {
        id: doctor.id,
        name: doctor.name,
        phone: doctor.phone,
        avatar: doctor.avatar,
        title: doctor.title,
        departmentId: doctor.departmentId,
        departmentName: doctor.departmentName,
        storeId: doctor.storeId,
        storeName: doctor.storeName,
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
    localStorage.removeItem('doctor');
    setInitialState({ currentDoctor: undefined });
    history.push('/login');
    message.success('已退出登录');
  };

  return {
    logo: '/logo.svg',
    title: '医生工作站',
    menu: { locale: false },
    rightContentRender: () => {
      if (!initialState?.currentDoctor) {
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
              src={initialState.currentDoctor.avatar}
            />
            <span>{initialState.currentDoctor.name}</span>
            {initialState.currentDoctor.title && (
              <span style={{ color: '#999', fontSize: 12 }}>
                ({initialState.currentDoctor.title})
              </span>
            )}
          </Space>
        </Dropdown>
      );
    },
    onPageChange: () => {
      if (!initialState?.currentDoctor && location.pathname !== '/login') {
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
