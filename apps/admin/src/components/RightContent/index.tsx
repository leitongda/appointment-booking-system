import { LogoutOutlined, UserOutlined, LockOutlined } from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import { Spin, Dropdown, Modal, Form, Input, App } from 'antd';
import type { MenuProps } from 'antd';
import React, { useState } from 'react';
import { removeToken } from '@hospital/shared';
import { adminApi } from '@hospital/api';

export const AvatarName: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};
  return <span className="anticon">{currentUser?.name || currentUser?.username}</span>;
};

export const AvatarDropdown: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { message } = App.useApp();
  const { initialState, setInitialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [form] = Form.useForm();

  const handleLogout = async () => {
    try {
      // 调用后端接口清除会话
      await adminApi.logout();
    } catch (error) {
      // 即使失败也继续清除本地状态
      console.error('退出登录请求失败:', error);
    }
    removeToken();
    setInitialState((s) => ({ ...s, currentUser: undefined }));
    history.push('/login');
  };

  const handleChangePassword = async (values: { oldPassword: string; newPassword: string; confirmPassword: string }) => {
    if (values.newPassword !== values.confirmPassword) {
      message.error('两次输入的新密码不一致');
      return;
    }
    
    setPasswordLoading(true);
    try {
      await adminApi.changePassword({
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      });
      message.success('密码修改成功，请重新登录');
      setPasswordModalVisible(false);
      form.resetFields();
      // 修改密码成功后退出登录
      setTimeout(() => {
        handleLogout();
      }, 1000);
    } catch (error: any) {
      message.error(error.message || '密码修改失败');
    } finally {
      setPasswordLoading(false);
    }
  };

  const menuItems: MenuProps['items'] = [
    {
      key: 'settings',
      icon: <UserOutlined />,
      label: '个人设置',
      onClick: () => history.push('/account/settings'),
    },
    {
      key: 'password',
      icon: <LockOutlined />,
      label: '修改密码',
      onClick: () => setPasswordModalVisible(true),
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
    <>
      <Dropdown menu={{ items: menuItems }} placement="bottomRight">
        {children}
      </Dropdown>

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={passwordLoading}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleChangePassword}
        >
          <Form.Item
            name="oldPassword"
            label="原密码"
            rules={[
              { required: true, message: '请输入原密码' },
              { min: 6, message: '密码至少6位' },
            ]}
          >
            <Input.Password placeholder="请输入原密码" />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6位' },
              { max: 20, message: '密码最多20位' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
