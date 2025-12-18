import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch, ProFormSelect } from '@ant-design/pro-components';
import { Card, App, Row, Col, Form } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { storeApi } from '@hospital/api';
import type { Store } from '@hospital/shared';
import { ProFormRegionSelector } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';

// 风格选项
const THEME_STYLE_OPTIONS = [
  { label: '中医-红', value: '中医-红' },
  { label: '中医-绿', value: '中医-绿' },
  { label: '现代-蓝', value: '现代-蓝' },
  { label: '简约-白', value: '简约-白' },
];

const StoreFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [store, setStore] = useState<Store | null>(null);

  useEffect(() => {
    if (isEdit) {
      loadStore();
    }
  }, [id]);

  const loadStore = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await storeApi.getDetail(id);
      setStore(data);
    } catch (error: any) {
      message.error('加载门店信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 处理地区数据：将region数组转换为province/city/district字段
      const { region, ...rest } = values;
      const [province, city, district] = region || [];
      const data = {
        ...rest,
        province,
        city,
        district,
        status: values.status ? 1 : 0
      };

      if (isEdit && id) {
        await storeApi.update(id, data);
        message.success('更新成功');
      } else {
        await storeApi.create(data);
        message.success('创建成功');
      }
      history.push('/store/list');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = store ? {
    ...store,
    region: [store.province, store.city, store.district].filter(Boolean),
    status: store.status === 1
  } : {
    status: true,
    sortOrder: 0,
    themeStyle: '中医-红'
  };

  return (
    <PageContainer title={isEdit ? '编辑门店' : '新增门店'}>
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
        {/* 基础信息 */}
        <Card title="基础信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="name"
              label="门店名称"
              width="md"
              rules={[{ required: true, message: '请输入门店名称' }]}
              placeholder="如：朴泽堂中医馆"
            />
            <ProFormText.Password
              name="password"
              label="门店密码"
              width="md"
              placeholder="请输入门店密码"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="phone"
              label="联系方式"
              width="md"
              placeholder="如：18984332758"
              rules={[{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]}
            />
            <ProFormText
              name="email"
              label="邮箱"
              width="md"
              placeholder="如：2544600916@qq.com"
              rules={[{ type: 'email', message: '请输入正确的邮箱地址' }]}
            />
          </ProForm.Group>
        </Card>

        {/* 地址信息 */}
        <Card title="地址信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProFormRegionSelector
            name="region"
            label="所在地区"
            width="md"
            placeholder="请选择省/市/区"
          />
          <ProFormTextArea
            name="address"
            label="门店地址"
            placeholder="如：贵州省贵阳市观山湖区金阳街道碧海南路与林城路西南侧国电新时代大楼1层7号"
            fieldProps={{ rows: 2 }}
          />
          <ProForm.Group>
            <ProFormText
              name="longitude"
              label="经度"
              width="sm"
              placeholder="如：106.619922"
            />
            <ProFormText
              name="latitude"
              label="纬度"
              width="sm"
              placeholder="如：26.644479"
            />
          </ProForm.Group>
        </Card>

        {/* 展示设置 */}
        <Card title="展示设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="xs"
              min={0}
              fieldProps={{ precision: 0 }}
              tooltip="数字越大越靠前"
            />
            <ProFormSelect
              name="themeStyle"
              label="风格选择"
              width="sm"
              options={THEME_STYLE_OPTIONS}
              placeholder="请选择风格"
            />
          </ProForm.Group>
          <Form.Item
            name="logo"
            label="Logo"
            tooltip="1:1比例，推荐尺寸：160px × 160px"
          >
            <ImageUpload
              aspectRatio="1:1"
              folder="store"
              placeholder="上传Logo"
              width={120}
              height={120}
            />
          </Form.Item>
        </Card>

        {/* 营业设置 */}
        <Card title="营业设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="openingTime"
              label="开始营业时间"
              width="sm"
              placeholder="如：08:00"
            />
            <ProFormText
              name="closingTime"
              label="结束营业时间"
              width="sm"
              placeholder="如：18:00"
            />
            <ProFormSwitch name="status" label="营业状态" />
          </ProForm.Group>
        </Card>

        {/* 其他信息 */}
        <Card title="其他信息" loading={loading}>
          <ProForm.Group>
            <ProFormText name="code" label="门店编码" width="md" />
            <ProFormText name="contactPerson" label="联系人" width="md" />
          </ProForm.Group>
          <ProFormTextArea
            name="description"
            label="门店简介"
            placeholder="请输入门店简介"
            fieldProps={{ rows: 3 }}
          />
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default StoreFormPage;

