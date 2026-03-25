import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDependency } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col, Divider } from 'antd';
import { history, useParams } from '@umijs/max';
import { useEffect, useState } from 'react';
import { miniappPlatformApi, storeApi } from '@hospital/api';
import type { MiniappInstanceCreateData, MiniappInstanceUpdateData, Store } from '@hospital/api';

const InstanceFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [stores, setStores] = useState<Store[]>([]);
  const [paymentProfiles, setPaymentProfiles] = useState<any[]>([]);
  const [checkingCode, setCheckingCode] = useState(false);
  const [checkingAppId, setCheckingAppId] = useState(false);

  // 模拟模板数据（实际应该从 API 获取）
  const templates = [
    { label: '患者端', value: 'patient' },
    { label: '医生端', value: 'doctor' },
  ];

  useEffect(() => {
    loadStores();
    loadPaymentProfiles();
    if (isEdit) {
      loadInstance();
    }
  }, [id]);

  const loadStores = async () => {
    try {
      const res = await storeApi.getStores({ page: 1, pageSize: 100 });
      setStores(res.data?.data || []);
    } catch (error) {
      console.error('加载门店列表失败:', error);
    }
  };

  const loadPaymentProfiles = async () => {
    try {
      const res = await miniappPlatformApi.getPaymentProfiles({ page: 1, pageSize: 100 });
      setPaymentProfiles(res.data?.data || []);
    } catch (error) {
      console.error('加载支付配置失败:', error);
    }
  };

  const loadInstance = async () => {
    setLoading(true);
    try {
      const res = await miniappPlatformApi.getMiniappInstance(id);
      const instance = res.data;
      form.setFieldsValue({
        code: instance.code,
        name: instance.name,
        appId: instance.appId,
        appSecretRef: instance.appSecretRef,
        uploadPrivateKeyRef: instance.uploadPrivateKeyRef,
        templateId: instance.templateId,
        templateVersionId: instance.templateVersionId,
        defaultStoreId: instance.defaultStoreId,
        defaultPaymentProfileId: instance.defaultPaymentProfileId,
        appConfig: instance.appConfig,
      });
    } catch (error) {
      message.error('加载实例信息失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

  const checkCode = async (_: any, value: string) => {
    if (!value) return Promise.resolve();

    // 编辑模式下，如果 code 没有变化，不需要检查
    if (isEdit) {
      const currentCode = form.getFieldValue('code');
      if (currentCode === value) return Promise.resolve();
    }

    setCheckingCode(true);
    try {
      const res = await miniappPlatformApi.checkInstanceUnique(code, undefined, isEdit ? id : undefined);
      if (res.data?.code_exists) {
        return Promise.reject(new Error('该实例编码已存在'));
      }
      return Promise.resolve();
    } catch (error) {
      return Promise.resolve();
    } finally {
      setCheckingCode(false);
    }
  };

  const checkAppId = async (_: any, value: string) => {
    if (!value) return Promise.resolve();

    // 编辑模式下，如果 app_id 没有变化，不需要检查
    if (isEdit) {
      const currentAppId = form.getFieldValue('appId');
      if (currentAppId === value) return Promise.resolve();
    }

    setCheckingAppId(true);
    try {
      const res = await miniappPlatformApi.checkInstanceUnique(undefined, value, isEdit ? id : undefined);
      if (res.data?.app_id_exists) {
        return Promise.reject(new Error('该 AppID 已存在'));
      }
      return Promise.resolve();
    } catch (error) {
      return Promise.resolve();
    } finally {
      setCheckingAppId(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (isEdit) {
        await miniappPlatformApi.updateMiniappInstance(id, values as MiniappInstanceUpdateData);
        message.success('更新成功');
      } else {
        await miniappPlatformApi.createMiniappInstance(values as MiniappInstanceCreateData);
        message.success('创建成功');
      }
      history.push('/miniapp-platform/instance');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <PageContainer title={isEdit ? '编辑小程序实例' : '新增小程序实例'}>
      <Card loading={loading}>
        <ProForm
          form={form}
          onFinish={handleSubmit}
          submitter={{
            searchConfig: { submitText: '保存' },
            resetText: '取消',
            onReset: () => history.back(),
          }}
        >
          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="name"
                label="实例名称"
                placeholder="请输入实例名称"
                rules={[{ required: true, message: '请输入实例名称' }]}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="code"
                label="实例编码"
                placeholder="请输入实例编码"
                rules={[
                  { validator: checkCode },
                ]}
                disabled={isEdit}
                extra="租户内唯一，用于系统识别"
                validateDebounce={500}
              />
            </Col>
          </Row>

          <Divider>微信小程序配置</Divider>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="appId"
                label="AppID"
                placeholder="请输入微信小程序AppID"
                rules={[
                  { required: true, message: '请输入微信小程序AppID' },
                  { validator: checkAppId },
                ]}
                validateDebounce={500}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="appSecretRef"
                label="AppSecret 引用"
                placeholder="例如: env:WX_APP_SECRET"
                extra="使用环境变量引用，格式: env:变量名"
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={24}>
              <ProFormText
                name="uploadPrivateKeyRef"
                label="上传私钥引用"
                placeholder="例如: env:WX_UPLOAD_PRIVATE_KEY"
                extra="使用环境变量引用，格式: env:变量名"
              />
            </Col>
          </Row>

          <Divider>模板配置</Divider>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormSelect
                name="templateId"
                label="模板"
                options={templates}
                placeholder="请选择模板"
                rules={[{ required: true, message: '请选择模板' }]}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="templateVersionId"
                label="模板版本"
                placeholder="请输入模板版本ID"
              />
            </Col>
          </Row>

          <Divider>默认配置</Divider>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormSelect
                name="defaultStoreId"
                label="默认门店"
                options={stores.map(s => ({ label: s.name, value: s.id }))}
                placeholder="请选择默认门店"
              />
            </Col>
            <Col span={12}>
              <ProFormSelect
                name="defaultPaymentProfileId"
                label="默认支付配置"
                options={paymentProfiles.map(p => ({ label: p.name, value: p.id }))}
                placeholder="请选择默认支付配置"
              />
            </Col>
          </Row>

          <Divider>扩展配置</Divider>

          <Row gutter={24}>
            <Col span={24}>
              <ProFormTextArea
                name="appConfig"
                label="实例扩展配置"
                placeholder="请输入 JSON 格式的扩展配置"
                fieldProps={{
                  rows: 4,
                }}
                extra="JSON 格式，用于存储实例特定的配置项"
              />
            </Col>
          </Row>
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default InstanceFormPage;
