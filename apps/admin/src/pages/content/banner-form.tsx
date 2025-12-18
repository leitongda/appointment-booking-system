import { PageContainer, ProForm, ProFormText, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App, Row, Col, Form } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Banner } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';

const LINK_TYPE_OPTIONS = [
  { label: '无链接', value: 0 },
  { label: '内部链接', value: 1 },
  { label: '外部链接', value: 2 },
];

const BannerFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<Banner | null>(null);

  useEffect(() => {
    if (isEdit) {
      loadBanner();
    }
  }, [id]);

  const loadBanner = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await contentApi.getBannerDetail(id);
      setBanner(data);
    } catch (error: any) {
      message.error('加载轮播图信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, status: values.status ? 1 : 0 };
      if (isEdit && id) {
        await contentApi.updateBanner(id, data);
        message.success('更新成功');
      } else {
        await contentApi.createBanner(data);
        message.success('创建成功');
      }
      history.push('/content/banner');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = banner ? {
    ...banner,
    status: banner.status === 1,
  } : {
    linkType: 0,
    position: 'home',
    sortOrder: 0,
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑轮播图' : '新增轮播图'}>
      <ProForm
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          searchConfig: { submitText: isEdit ? '保存' : '创建' },
          resetButtonProps: { style: { display: 'none' } },
          render: (_, dom) => (
            <Row>
              <Col span={24} style={{ textAlign: 'center' }}>
                {dom}
              </Col>
            </Row>
          ),
        }}
      >
        <Card title="轮播图信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProFormText name="title" label="标题" width="lg" />
          <Form.Item name="imageUrl" label="轮播图片" rules={[{ required: true, message: '请上传轮播图片' }]}>
            <ImageUpload
              aspectRatio="16:9"
              folder="banner"
              placeholder="上传轮播图"
              width={320}
              height={180}
            />
          </Form.Item>
        </Card>

        <Card title="链接设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="linkType"
              label="链接类型"
              width="md"
              options={LINK_TYPE_OPTIONS}
            />
            <ProFormSelect
              name="position"
              label="展示位置"
              width="md"
              options={[{ label: '首页', value: 'home' }, { label: '我的', value: 'mine' }]}
            />
          </ProForm.Group>
          <ProFormText
            name="linkUrl"
            label="链接地址"
            width="lg"
            placeholder="请输入链接地址"
          />
        </Card>

        <Card title="其他设置" loading={loading}>
          <ProForm.Group>
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="sm"
              min={0}
            />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default BannerFormPage;

