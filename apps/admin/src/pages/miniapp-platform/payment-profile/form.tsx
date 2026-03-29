import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormSwitch } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col, Divider } from 'antd';
import { history, useParams } from '@umijs/max';
import { useEffect, useState } from 'react';
import { miniappPlatformApi } from '@hospital/api';
import type { PaymentProfileCreateData, PaymentProfileUpdateData, Company } from '@hospital/api';

const PaymentProfileFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [checkingCode, setCheckingCode] = useState(false);
  const [companies, setCompanies] = useState<Company[]>([]);

  useEffect(() => {
    loadCompanies();
    if (isEdit) {
      loadProfile();
    }
  }, [id]);

  const loadCompanies = async () => {
    try {
      const res = await miniappPlatformApi.getCompanies({ page: 1, pageSize: 100 });
      setCompanies(res.data?.data || []);
    } catch (error) {
      console.error('加载公司列表失败:', error);
    }
  };

  const loadProfile = async () => {
    setLoading(true);
    try {
      const res = await miniappPlatformApi.getPaymentProfile(id);
      const profile = res.data;
      form.setFieldsValue({
        name: profile.name,
        code: profile.code,
        mode: profile.mode,
        appId: profile.appId,
        mchId: profile.mchId,
        subMchid: profile.subMchid,
        notifyUrl: profile.notifyUrl,
        apiV3KeyRef: profile.apiV3KeyRef,
        certSerialNo: profile.certSerialNo,
        privateKeyRef: profile.privateKeyRef,
        companyId: profile.companyId,
        isDefault: profile.isDefault,
      });
    } catch (error) {
      message.error('加载支付配置失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

  const checkProfileCode = async (_: any, value: string) => {
    if (!value) return Promise.resolve();

    // 编辑模式下，如果 code 没有变化，不需要检查
    if (isEdit) {
      const currentCode = form.getFieldValue('code');
      if (currentCode === value) return Promise.resolve();
    }

    setCheckingCode(true);
    try {
      const res = await miniappPlatformApi.checkPaymentProfileCodeUnique(value, isEdit ? id : undefined);
      if (res.data?.exists) {
        return Promise.reject(new Error('该支付配置编码已存在'));
      }
      return Promise.resolve();
    } catch (error) {
      return Promise.resolve();
    } finally {
      setCheckingCode(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (isEdit) {
        await miniappPlatformApi.updatePaymentProfile(id, values as PaymentProfileUpdateData);
        message.success('更新成功');
      } else {
        await miniappPlatformApi.createPaymentProfile(values as PaymentProfileCreateData);
        message.success('创建成功');
      }
      history.push('/platform/miniapp-platform/payment-profile');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <PageContainer title={isEdit ? '编辑支付配置' : '新增支付配置'}>
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
                label="配置名称"
                placeholder="请输入配置名称"
                rules={[{ required: true, message: '请输入配置名称' }]}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="code"
                label="配置编码"
                placeholder="请输入配置编码"
                rules={[
                  { validator: checkProfileCode },
                ]}
                disabled={isEdit}
                extra="租户内唯一，用于系统识别"
                validateDebounce={500}
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormSelect
                name="mode"
                label="支付模式"
                options={[
                  { label: '直连', value: 'direct' },
                  { label: '服务商', value: 'service_provider' },
                ]}
                placeholder="请选择支付模式"
                rules={[{ required: true, message: '请选择支付模式' }]}
              />
            </Col>
            <Col span={12}>
              <ProFormSelect
                name="companyId"
                label="所属公司"
                options={companies.map(c => ({ label: c.name, value: c.id }))}
                placeholder="请选择所属公司"
              />
            </Col>
          </Row>

          {!isEdit && (
            <Row gutter={24}>
              <Col span={12}>
                <ProFormSwitch
                  name="isDefault"
                  label="设为默认"
                  checkedChildren="是"
                  unCheckedChildren="否"
                  extra="租户的默认支付配置"
                />
              </Col>
            </Row>
          )}

          <Divider>微信支付配置</Divider>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="appId"
                label="AppID"
                placeholder="请输入微信AppID"
                rules={[{ required: true, message: '请输入微信AppID' }]}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="mchId"
                label="商户号"
                placeholder="请输入商户号"
                tooltip="直连模式必填"
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="subMchid"
                label="子商户号"
                placeholder="请输入子商户号"
                tooltip="服务商模式必填"
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="notifyUrl"
                label="支付回调地址"
                placeholder="请输入支付回调地址"
              />
            </Col>
          </Row>

          <Divider>敏感信息（环境变量引用）</Divider>

          <Row gutter={24}>
            <Col span={24}>
              <ProFormText
                name="apiV3KeyRef"
                label="APIv3 Key 引用"
                placeholder="例如: env:WX_API_V3_KEY"
                extra="使用环境变量引用，格式: env:变量名"
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="certSerialNo"
                label="证书序列号"
                placeholder="请输入证书序列号"
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="privateKeyRef"
                label="商户私钥引用"
                placeholder="例如: env:WX_PRIVATE_KEY"
                extra="使用环境变量引用，格式: env:变量名"
              />
            </Col>
          </Row>
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default PaymentProfileFormPage;
