import { PageContainer, ProForm, ProFormText } from '@ant-design/pro-components';
import { Card, App, Row, Col, Typography, Space, Spin } from 'antd';
import { useState, useEffect } from 'react';
import { useModel } from '@umijs/max';
import { adminApi } from '@hospital/api';
import type { Admin } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';

const { Title, Text } = Typography;

const AccountSettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const { initialState, setInitialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(false);
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>();
  const [avatarSaving, setAvatarSaving] = useState(false);

  useEffect(() => {
    loadAdmin();
  }, []);

  const loadAdmin = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getCurrentAdmin();
      setAdmin(data);
      setAvatarUrl(data.avatar);
    } catch (error) {
      console.error('加载用户信息失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 头像变更时自动保存
  const handleAvatarChange = async (url: string | undefined) => {
    setAvatarUrl(url);
    if (url === admin?.avatar) return; // 没有变化不需要保存
    
    setAvatarSaving(true);
    try {
      const updatedAdmin = await adminApi.updateProfile({ avatar: url });
      message.success('头像更新成功');
      setAdmin(updatedAdmin);
      // 更新全局状态
      if (initialState) {
        setInitialState({
          ...initialState,
          currentUser: updatedAdmin,
        });
      }
    } catch (error: any) {
      message.error(error.message || '头像更新失败');
      // 恢复原来的头像
      setAvatarUrl(admin?.avatar);
    } finally {
      setAvatarSaving(false);
    }
  };

  const handleSubmit = async (values: { name?: string; phone?: string; email?: string }) => {
    try {
      const updatedAdmin = await adminApi.updateProfile(values);
      message.success('保存成功');
      setAdmin(updatedAdmin);
      // 更新全局状态
      if (initialState) {
        setInitialState({
          ...initialState,
          currentUser: updatedAdmin,
        });
      }
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  return (
    <PageContainer title="个人设置">
      <Spin spinning={loading}>
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={24} align="middle">
            <Col>
              <Spin spinning={avatarSaving}>
                <ImageUpload
                  value={avatarUrl}
                  onChange={handleAvatarChange}
                  aspectRatio="1:1"
                  width={100}
                  height={100}
                  folder="avatars"
                  placeholder="上传头像"
                  allowUrlTransfer={false}
                  showCrop={true}
                />
              </Spin>
            </Col>
            <Col>
              <Space direction="vertical" size={4}>
                <Title level={4} style={{ margin: 0 }}>
                  {admin?.name || admin?.username}
                </Title>
                <Text type="secondary">用户名：{admin?.username}</Text>
                <Text type="secondary">角色：{admin?.roleName || '-'}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>点击左侧可更换头像</Text>
              </Space>
            </Col>
          </Row>
        </Card>

        <Card title="基本信息">
          <ProForm
            onFinish={handleSubmit}
            initialValues={{
              name: admin?.name,
              phone: admin?.phone,
              email: admin?.email,
            }}
            submitter={{
              searchConfig: { submitText: '保存' },
              resetButtonProps: { style: { display: 'none' } },
            }}
          >
            <ProForm.Group>
              <ProFormText
                name="name"
                label="姓名"
                width="md"
                placeholder="请输入姓名"
                fieldProps={{ autoComplete: 'off' }}
              />
              <ProFormText
                name="phone"
                label="手机号"
                width="md"
                placeholder="请输入手机号"
                rules={[
                  { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
                ]}
                fieldProps={{ autoComplete: 'off' }}
              />
            </ProForm.Group>
            <ProFormText
              name="email"
              label="邮箱"
              width="md"
              placeholder="请输入邮箱"
              rules={[
                { type: 'email', message: '邮箱格式不正确' },
              ]}
              fieldProps={{ autoComplete: 'off' }}
            />
          </ProForm>
        </Card>
      </Spin>
    </PageContainer>
  );
};

export default AccountSettingsPage;

