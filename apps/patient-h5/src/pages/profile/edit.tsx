import { NavBar, Form, Input, Button, Toast, ImageUploader } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { userApi, uploadApi } from '@hospital/api';
import type { User } from '@hospital/shared';
import type { ImageUploadItem } from 'antd-mobile/es/components/image-uploader';
import styles from './edit.less';

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
        nickname: data.nickname || data.name,
        email: data.email,
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
      email: values.email,
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
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>编辑资料</NavBar>

      <div className={styles.avatarSection}>
        <div className={styles.avatarLabel}>头像</div>
        <ImageUploader
          value={fileList}
          onChange={setFileList}
          upload={handleUpload}
          maxCount={1}
          className={styles.avatarUploader}
        />
      </div>

      <Form
        form={form}
        layout="horizontal"
        className={styles.form}
      >
        <Form.Item
          name="nickname"
          label="昵称"
          rules={[{ required: true, message: '请输入昵称' }]}
        >
          <Input placeholder="请输入昵称" />
        </Form.Item>

        <Form.Item
          name="email"
          label="邮箱"
          rules={[
            { type: 'email', message: '请输入正确的邮箱地址' },
          ]}
        >
          <Input placeholder="请输入邮箱（选填）" type="email" />
        </Form.Item>

        <Form.Item label="手机号">
          <Input 
            value={user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')} 
            disabled 
          />
        </Form.Item>
      </Form>

      <div className={styles.footer}>
        <Button
          block
          color="primary"
          size="large"
          loading={submitting}
          onClick={handleSubmit}
        >
          保存
        </Button>
      </div>
    </div>
  );
};

export default ProfileEditPage;

