import { NavBar, Form, Input, Toast, ImageUploader, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { userApi, uploadApi, useEmailBinding } from '@hospital/api';
import type { User } from '@hospital/shared';
import type { ImageUploadItem } from 'antd-mobile/es/components/image-uploader';
import { Button, Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';
import EmailBindingDialog from '@/components/EmailBindingDialog';

const ProfileEditPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [fileList, setFileList] = useState<ImageUploadItem[]>([]);

  // 邮箱管理：统一使用共享 hook（默认 accountApi）
  const emailBinding = useEmailBinding({
    currentEmail: user?.email,
    onSuccess: async (mode) => {
      if (mode === 'bind') Toast.show({ content: '邮箱绑定成功', icon: 'success' });
      else if (mode === 'unbind') Toast.show({ content: '邮箱解绑成功', icon: 'success' });
      else Toast.show({ content: '邮箱换绑成功', icon: 'success' });
      await loadProfile();
    },
    onError: (error) => {
      Toast.show({ content: (error as any)?.message || '操作失败', icon: 'fail' });
    },
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await userApi.getProfile();
      setUser(data);
      form.setFieldsValue({
        nickname: data.nickname,
      });
      if (data.avatar) {
        setFileList([{ url: data.avatar }]);
      }
    } catch (error) {
      Toast.show({ content: '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file: File): Promise<ImageUploadItem> => {
    try {
      const result = await uploadApi.upload(file, 'avatars');
      return { url: result.url };
    } catch (error) {
      Toast.show({ content: '上传失败', icon: 'fail' });
      throw error;
    }
  };

  const handleSubmit = async () => {
    try {
      await form.validateFields();
    } catch {
      return;
    }

    const values = form.getFieldsValue();
    const updateData: Partial<User> = {
      nickname: values.nickname,
    };

    // 如果有新上传的头像
    if (fileList.length > 0 && fileList[0].url) {
      updateData.avatar = fileList[0].url;
    }

    setSubmitting(true);
    try {
      await userApi.updateProfile(updateData);
      Toast.show({ content: '保存成功', icon: 'success' });
      history.back();
    } catch (error: any) {
      Toast.show({ content: error.message || '保存失败', icon: 'fail' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <NavBar
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        编辑资料
      </NavBar>

      <motion.div
        className="p-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Avatar Section */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground font-medium">头像</span>
              <ImageUploader
                value={fileList}
                onChange={setFileList}
                upload={handleUpload}
                maxCount={1}
                className="[&_.adm-image-uploader-cell]:!w-16 [&_.adm-image-uploader-cell]:!h-16 [&_.adm-image-uploader-cell]:!rounded-full"
              />
            </div>
          </Card>
        </motion.div>

        {/* Form Section */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="none" className="overflow-hidden">
            <Form
              form={form}
              layout="horizontal"
              className="[&_.adm-list-item]:min-h-[52px]"
            >
              <Form.Item
                name="nickname"
                label="昵称"
                rules={[{ required: true, message: '请输入昵称' }]}
              >
                <Input placeholder="请输入昵称" className="text-right" />
              </Form.Item>

              <Form.Item label="手机号">
                <Input
                  value={user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                  disabled
                  className="text-right text-muted-foreground"
                />
              </Form.Item>

              <Form.Item label="邮箱" onClick={() => {
                if (user?.email) {
                  // 已绑定邮箱：用 action sheet 让用户选择换绑/解绑
                  Dialog.show({
                    title: '邮箱管理',
                    closeOnAction: true,
                    actions: [
                      [
                        {
                          key: 'change',
                          text: '更换邮箱',
                          onClick: () => emailBinding.openModal('change'),
                        },
                        {
                          key: 'unbind',
                          text: '解绑邮箱',
                          bold: true,
                          danger: true,
                          onClick: () => emailBinding.openModal('unbind'),
                        },
                      ],
                      [
                        {
                          key: 'cancel',
                          text: '取消',
                        },
                      ],
                    ],
                    content: (
                      <div style={{ textAlign: 'center', padding: '8px 0' }}>
                        <div style={{ fontSize: 14, color: '#999', marginBottom: 4 }}>当前绑定邮箱</div>
                        <div style={{ fontSize: 16, fontWeight: 500 }}>{user.email}</div>
                      </div>
                    ),
                  });
                } else {
                  emailBinding.openModal('bind');
                }
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                  {user?.email ? (
                    <>
                      <span style={{ color: '#999' }}>{user.email}</span>
                      <span style={{ color: '#52c41a', fontSize: 12 }}>已绑定</span>
                    </>
                  ) : (
                    <span style={{ color: '#1677ff' }}>去绑定</span>
                  )}
                </div>
              </Form.Item>
            </Form>
          </Card>
        </motion.div>
      </motion.div>

      {/* Fixed Footer */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/80 backdrop-blur-sm border-t border-border">
        <Button
          variant="primary"
          className="w-full"
          disabled={submitting}
          onClick={handleSubmit}
        >
          {submitting ? '保存中...' : '保存'}
        </Button>
      </div>

      {/* 邮箱管理弹窗 */}
      <EmailBindingDialog binding={emailBinding} currentEmail={user?.email} />
    </div>
  );
};

export default ProfileEditPage;
