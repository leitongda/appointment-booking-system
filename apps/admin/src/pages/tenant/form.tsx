import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDigit } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col } from 'antd';
import { history, useParams, useSearchParams } from '@umijs/max';
import { useEffect, useRef, useState } from 'react';
import { tenantApi } from '@hospital/api';
import type { SubscriptionPlan, TenantCreateData, TenantUpdateData } from '@hospital/api';

const TenantFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [checkingCode, setCheckingCode] = useState(false);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    loadPlans();
    if (isEdit) {
      loadTenant();
    }
    return () => {
      cancelledRef.current = true;
    };
  }, [id]);

  const loadPlans = async () => {
    try {
      const res = await tenantApi.getPlans(1);
      if (cancelledRef.current) return;
      setPlans(Array.isArray(res) ? res : []);
    } catch (error) {
      console.error('加载订阅计划失败:', error);
    }
  };

  const loadTenant = async () => {
    setLoading(true);
    try {
      const res = await tenantApi.getTenant(id);
      if (cancelledRef.current) return;
      const tenant = res;
      form.setFieldsValue({
        tenantCode: tenant.tenantCode,
        name: tenant.name,
        subscriptionPlanId: tenant.subscriptionPlanId,
        billingCycle: tenant.billingCycle || 'monthly',
        maxStores: tenant.maxStores,
        maxAdmins: tenant.maxAdmins,
        maxDoctors: tenant.maxDoctors,
        maxAppointmentsPerMonth: tenant.maxAppointmentsPerMonth,
        contactName: tenant.contactName,
        contactPhone: tenant.contactPhone,
        contactEmail: tenant.contactEmail,
        address: tenant.address,
        customDomain: tenant.customDomain,
        subdomain: tenant.subdomain,
      });
    } catch (error) {
      if (cancelledRef.current) return;
      message.error('加载租户信息失败');
      history.back();
    } finally {
      if (!cancelledRef.current) {
        setLoading(false);
      }
    }
  };

  const checkTenantCode = async (_: any, value: string) => {
    if (!value) return Promise.resolve();
    if (!/^[a-z0-9-]+$/.test(value)) {
      return Promise.reject(new Error('只能包含小写字母、数字和连字符'));
    }
    if (value.length < 3 || value.length > 50) {
      return Promise.reject(new Error('长度需在 3-50 个字符之间'));
    }

    // 编辑模式下，如果 code 没有变化，不需要检查
    if (isEdit) {
      const currentCode = form.getFieldValue('tenantCode');
      if (currentCode === value) return Promise.resolve();
    }

    setCheckingCode(true);
    try {
      const res = await tenantApi.checkTenantCodeUnique(value, isEdit ? id : undefined);
      if (res?.exists) {
        return Promise.reject(new Error('该租户标识已存在'));
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
        await tenantApi.updateTenant(id, values as TenantUpdateData);
        message.success('更新成功');
      } else {
        await tenantApi.createTenant(values as TenantCreateData);
        message.success('创建成功');
      }
      history.push('/platform/tenant');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <PageContainer title={isEdit ? '编辑租户' : '新增租户'}>
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
                name="tenantCode"
                label="租户标识"
                placeholder="请输入租户标识"
                rules={
                  isEdit
                    ? []
                    : [
                        { required: true, message: '请输入租户标识' },
                        { validator: checkTenantCode },
                      ]
                }
                disabled={isEdit}
                extra="只能包含小写字母、数字和连字符，长度 3-50"
                validateDebounce={500}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="name"
                label="租户名称"
                placeholder="请输入租户名称"
                rules={[{ required: true, message: '请输入租户名称' }]}
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormSelect
                name="subscriptionPlanId"
                label="订阅计划"
                options={plans.map(p => ({ label: p.name, value: p.id }))}
                placeholder="请选择订阅计划"
              />
            </Col>
            <Col span={12}>
              <ProFormSelect
                name="billingCycle"
                label="计费周期"
                options={[
                  { label: '月付', value: 'monthly' },
                  { label: '年付', value: 'yearly' },
                ]}
                initialValue="monthly"
              />
            </Col>
          </Row>

          <Card title="配额设置" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={6}>
                <ProFormDigit
                  name="maxStores"
                  label="最大门店数"
                  min={1}
                  placeholder="使用计划默认值"
                />
              </Col>
              <Col span={6}>
                <ProFormDigit
                  name="maxAdmins"
                  label="最大管理员数"
                  min={1}
                  placeholder="使用计划默认值"
                />
              </Col>
              <Col span={6}>
                <ProFormDigit
                  name="maxDoctors"
                  label="最大医生数"
                  min={1}
                  placeholder="使用计划默认值"
                />
              </Col>
              <Col span={6}>
                <ProFormDigit
                  name="maxAppointmentsPerMonth"
                  label="月预约上限"
                  min={1}
                  placeholder="使用计划默认值"
                />
              </Col>
            </Row>
          </Card>

          <Card title="联系信息" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={8}>
                <ProFormText
                  name="contactName"
                  label="联系人"
                  placeholder="请输入联系人姓名"
                />
              </Col>
              <Col span={8}>
                <ProFormText
                  name="contactPhone"
                  label="联系电话"
                  placeholder="请输入联系电话"
                />
              </Col>
              <Col span={8}>
                <ProFormText
                  name="contactEmail"
                  label="联系邮箱"
                  placeholder="请输入联系邮箱"
                  rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
                />
              </Col>
            </Row>
            <Row gutter={24}>
              <Col span={24}>
                <ProFormTextArea
                  name="address"
                  label="详细地址"
                  placeholder="请输入详细地址"
                  rows={2}
                />
              </Col>
            </Row>
          </Card>

          <Card title="域名配置" size="small">
            <Row gutter={24}>
              <Col span={12}>
                <ProFormText
                  name="subdomain"
                  label="子域名前缀"
                  placeholder="例如: clinic1"
                  extra="访问地址: clinic1.yourdomain.com"
                />
              </Col>
              <Col span={12}>
                <ProFormText
                  name="customDomain"
                  label="自定义域名"
                  placeholder="例如: www.example.com"
                />
              </Col>
            </Row>
          </Card>
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default TenantFormPage;
