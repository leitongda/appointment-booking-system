import { NavBar, Form, Input, Toast, ImageUploader } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { userApi, uploadApi } from '@hospital/api';
import type { User } from '@hospital/shared';
import type { ImageUploadItem } from 'antd-mobile/es/components/image-uploader';
import { Button, Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const ProfileEditPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [fileList, setFileList] = useState<ImageUploadItem[]>([]);

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
    </div>
  );
};

export default ProfileEditPage;
