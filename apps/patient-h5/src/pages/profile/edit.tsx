import { NavBar, Form, Input, Toast, ImageUploader, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { userApi, uploadApi, authApi } from '@hospital/api';
import type { User } from '@hospital/shared';
import type { ImageUploadItem } from 'antd-mobile/es/components/image-uploader';
import { Button, Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

type EmailAction = 'bind' | 'unbind' | 'change';

const ProfileEditPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [fileList, setFileList] = useState<ImageUploadItem[]>([]);

  // 邮箱管理状态
  const [emailDialogVisible, setEmailDialogVisible] = useState(false);
  const [emailAction, setEmailAction] = useState<EmailAction>('bind');
  const [emailValue, setEmailValue] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [oldEmailCode, setOldEmailCode] = useState('');
  const [emailCodeSending, setEmailCodeSending] = useState(false);
  const [emailCodeCountdown, setEmailCodeCountdown] = useState(0);
  const [oldEmailCodeSending, setOldEmailCodeSending] = useState(false);
  const [oldEmailCodeCountdown, setOldEmailCodeCountdown] = useState(0);
  const [emailSubmitting, setEmailSubmitting] = useState(false);
  const emailTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const emailOldTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadProfile();
    return () => {
      if (emailTimerRef.current) clearInterval(emailTimerRef.current);
      if (emailOldTimerRef.current) clearInterval(emailOldTimerRef.current);
    };
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

  // ========== 邮箱管理 ==========

  const openEmailDialog = (action: EmailAction) => {
    setEmailAction(action);
    setEmailValue('');
    setEmailCode('');
    setOldEmailCode('');
    setEmailCodeCountdown(0);
    setOldEmailCodeCountdown(0);
    if (emailTimerRef.current) {
      clearInterval(emailTimerRef.current);
      emailTimerRef.current = null;
    }
    if (emailOldTimerRef.current) {
      clearInterval(emailOldTimerRef.current);
      emailOldTimerRef.current = null;
    }
    setEmailDialogVisible(true);
  };

  const handleSendEmailCode = async (target: 'new' | 'old' = 'new') => {
    try {
      if (target === 'new') {
        if (!emailValue) {
          Toast.show({ content: '请先输入邮箱', icon: 'fail' });
          return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue)) {
          Toast.show({ content: '邮箱格式不正确', icon: 'fail' });
          return;
        }
        setEmailCodeSending(true);
        await authApi.sendEmailCode(emailValue, 'bind');
        Toast.show({ content: '验证码已发送', icon: 'success' });
        setEmailCodeCountdown(60);
        emailTimerRef.current = setInterval(() => {
          setEmailCodeCountdown((prev) => {
            if (prev <= 1) {
              if (emailTimerRef.current) {
                clearInterval(emailTimerRef.current);
                emailTimerRef.current = null;
              }
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } else {
        if (!user?.email) {
          Toast.show({ content: '当前未绑定邮箱', icon: 'fail' });
          return;
        }
        setOldEmailCodeSending(true);
        await authApi.sendEmailCode(user.email, 'bind');
        Toast.show({ content: '验证码已发送到当前邮箱', icon: 'success' });
        setOldEmailCodeCountdown(60);
        emailOldTimerRef.current = setInterval(() => {
          setOldEmailCodeCountdown((prev) => {
            if (prev <= 1) {
              if (emailOldTimerRef.current) {
                clearInterval(emailOldTimerRef.current);
                emailOldTimerRef.current = null;
              }
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    } catch (error: any) {
      Toast.show({ content: error.message || '发送验证码失败', icon: 'fail' });
    } finally {
      setEmailCodeSending(false);
      setOldEmailCodeSending(false);
    }
  };

  const handleEmailSubmit = async () => {
    try {
      setEmailSubmitting(true);

      if (emailAction === 'bind') {
        if (!emailValue || !emailCode) {
          Toast.show({ content: '请填写完整信息', icon: 'fail' });
          return;
        }
        await authApi.emailBind({ email: emailValue, code: emailCode });
        Toast.show({ content: '邮箱绑定成功', icon: 'success' });
      } else if (emailAction === 'unbind') {
        if (!emailCode) {
          Toast.show({ content: '请输入验证码', icon: 'fail' });
          return;
        }
        await authApi.emailUnbind({ code: emailCode });
        Toast.show({ content: '邮箱解绑成功', icon: 'success' });
      } else if (emailAction === 'change') {
        if (!emailValue || !emailCode || !oldEmailCode) {
          Toast.show({ content: '请填写完整信息', icon: 'fail' });
          return;
        }
        await authApi.emailChange({
          newEmail: emailValue,
          newEmailCode: emailCode,
          oldEmailCode: oldEmailCode,
        });
        Toast.show({ content: '邮箱换绑成功', icon: 'success' });
      }

      setEmailDialogVisible(false);
      // 刷新用户信息
      await loadProfile();
    } catch (error: any) {
      Toast.show({ content: error.message || '操作失败', icon: 'fail' });
    } finally {
      setEmailSubmitting(false);
    }
  };

  const renderEmailDialogContent = () => {
    switch (emailAction) {
      case 'bind':
        return (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>邮箱地址</div>
              <Input
                placeholder="请输入邮箱地址"
                value={emailValue}
                onChange={setEmailValue}
                clearable
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>验证码</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  placeholder="请输入验证码"
                  value={emailCode}
                  onChange={setEmailCode}
                  maxLength={6}
                  clearable
                  style={{ flex: 1 }}
                />
                <Button
                  size="sm"
                  disabled={emailCodeCountdown > 0 || emailCodeSending}
                  onClick={() => handleSendEmailCode('new')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {emailCodeSending ? '发送中' : emailCodeCountdown > 0 ? `${emailCodeCountdown}s` : '获取验证码'}
                </Button>
              </div>
            </div>
          </>
        );
      case 'unbind':
        return (
          <>
            <div style={{ marginBottom: 12, fontSize: 14, color: '#666' }}>
              验证码将发送到当前绑定的邮箱：<strong>{user?.email}</strong>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>验证码</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  placeholder="请输入验证码"
                  value={emailCode}
                  onChange={setEmailCode}
                  maxLength={6}
                  clearable
                  style={{ flex: 1 }}
                />
                <Button
                  size="sm"
                  disabled={emailCodeCountdown > 0 || emailCodeSending}
                  onClick={() => handleSendEmailCode('new')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {emailCodeSending ? '发送中' : emailCodeCountdown > 0 ? `${emailCodeCountdown}s` : '获取验证码'}
                </Button>
              </div>
            </div>
          </>
        );
      case 'change':
        return (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>新邮箱地址</div>
              <Input
                placeholder="请输入新邮箱地址"
                value={emailValue}
                onChange={setEmailValue}
                clearable
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>新邮箱验证码</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  placeholder="请输入新邮箱验证码"
                  value={emailCode}
                  onChange={setEmailCode}
                  maxLength={6}
                  clearable
                  style={{ flex: 1 }}
                />
                <Button
                  size="sm"
                  disabled={emailCodeCountdown > 0 || emailCodeSending}
                  onClick={() => handleSendEmailCode('new')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {emailCodeSending ? '发送中' : emailCodeCountdown > 0 ? `${emailCodeCountdown}s` : '获取验证码'}
                </Button>
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>
                旧邮箱验证码（{user?.email || '当前邮箱'}）
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  placeholder="请输入旧邮箱验证码"
                  value={oldEmailCode}
                  onChange={setOldEmailCode}
                  maxLength={6}
                  clearable
                  style={{ flex: 1 }}
                />
                <Button
                  size="sm"
                  disabled={oldEmailCodeCountdown > 0 || oldEmailCodeSending}
                  onClick={() => handleSendEmailCode('old')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {oldEmailCodeSending ? '发送中' : oldEmailCodeCountdown > 0 ? `${oldEmailCodeCountdown}s` : '获取验证码'}
                </Button>
              </div>
            </div>
          </>
        );
    }
  };

  const getEmailDialogTitle = () => {
    switch (emailAction) {
      case 'bind': return '绑定邮箱';
      case 'unbind': return '解绑邮箱';
      case 'change': return '更换邮箱';
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
                  // 已绑定邮箱，显示操作选择
                  Dialog.show({
                    title: '邮箱管理',
                    closeOnAction: true,
                    actions: [
                      [
                        {
                          key: 'change',
                          text: '更换邮箱',
                          onClick: () => openEmailDialog('change'),
                        },
                        {
                          key: 'unbind',
                          text: '解绑邮箱',
                          bold: true,
                          danger: true,
                          onClick: () => openEmailDialog('unbind'),
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
                  openEmailDialog('bind');
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
      <Dialog
        visible={emailDialogVisible}
        title={getEmailDialogTitle()}
        content={
          <div style={{ padding: '8px 0' }}>
            {renderEmailDialogContent()}
          </div>
        }
        closeOnAction
        actions={[
          [
            {
              key: 'cancel',
              text: '取消',
              onClick: () => setEmailDialogVisible(false),
            },
            {
              key: 'confirm',
              text: emailSubmitting ? '提交中...' : '确认',
              bold: true,
              disabled: emailSubmitting,
              onClick: async (e?: React.MouseEvent) => {
                // 阻止 Dialog 自动关闭，由 handleEmailSubmit 控制
                e?.preventDefault?.();
                await handleEmailSubmit();
              },
            },
          ],
        ]}
        onClose={() => setEmailDialogVisible(false)}
      />
    </div>
  );
};

export default ProfileEditPage;
