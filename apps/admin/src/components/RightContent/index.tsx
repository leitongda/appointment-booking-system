import { LogoutOutlined, SettingOutlined, UserOutlined } from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import { Spin, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import React from 'react';
import { removeToken } from '@hospital/shared';

export const AvatarName: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};
  return <span className="anticon">{currentUser?.name || currentUser?.username}</span>;
};

export const AvatarDropdown: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { initialState, setInitialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};

  const handleLogout = async () => {
    removeToken();
    setInitialState((s) => ({ ...s, currentUser: undefined }));
    history.push('/login');
  };

  const menuItems: MenuProps['items'] = [
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '个人设置',
      onClick: () => history.push('/system/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  if (!currentUser) {
    return (
      <span>
        <Spin size="small" style={{ marginLeft: 8, marginRight: 8 }} />
      </span>
    );
  }

  return (
    <Dropdown menu={{ items: menuItems }} placement="bottomRight">
      {children}
    </Dropdown>
  );
};

