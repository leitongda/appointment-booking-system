import { Form, Input, Toast, NavBar } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { userApi } from '@hospital/api';
import { Button, Card, GradientText } from '@/components/ui';
import { fadeInUp } from '@/components/ui/animations';

const ChangePasswordPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const onFinish = async (values: { oldPassword: string; newPassword: string; confirmPassword: string }) => {
    if (values.newPassword !== values.confirmPassword) {
      Toast.show({ content: '两次输入的新密码不一致', icon: 'fail' });
      return;
    }

    // 验证密码长度
    if (values.newPassword.length < 6 || values.newPassword.length > 20) {
      Toast.show({ content: '密码长度必须为6-20位', icon: 'fail' });
      return;
    }

    // 验证新旧密码不能相同
    if (values.oldPassword === values.newPassword) {
      Toast.show({ content: '新密码不能与原密码相同', icon: 'fail' });
      return;
    }

    setLoading(true);
    try {
      await userApi.changePassword({
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      });
      Toast.show({ content: '密码修改成功', icon: 'success' });
      form.resetFields();
      setTimeout(() => {
        history.back();
      }, 1000);
    } catch (error: any) {
      Toast.show({ content: error.message || '密码修改失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar onBack={() => history.back()}>修改密码</NavBar>

      <motion.div
        className="px-4 py-6"
        variants={fadeInUp}
        initial="hidden"
        animate="visible"
      >
        <Card padding="lg">
          <Form
            form={form}
            layout="vertical"
            footer={null}
            onFinish={onFinish}
          >
            <Form.Item
              name="oldPassword"
              label="原密码"
              rules={[
                { required: true, message: '请输入原密码' },
                { min: 6, message: '密码至少6位' },
              ]}
            >
              <Input
                placeholder="请输入原密码"
                type="password"
                clearable
              />
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
              <Input
                placeholder="请输入新密码（6-20位）"
                type="password"
                clearable
              />
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
              <Input
                placeholder="请再次输入新密码"
                type="password"
                clearable
              />
            </Form.Item>

            <div className="mt-6">
              <Button
                block
                type="submit"
                loading={loading}
              >
                确认修改
              </Button>
            </div>
          </Form>
        </Card>

        <motion.div
          className="mt-6 text-center"
          variants={fadeInUp}
        >
          <p className="text-sm text-muted-foreground">
            密码长度为6-20位，建议使用字母、数字和符号组合
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default ChangePasswordPage;
