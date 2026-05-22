import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col, Space } from 'antd';
import { history, useParams, useSearchParams } from '@umijs/max';
import { useEffect, useRef, useState } from 'react';
import { tenantApi } from '@hospital/api';
import type { SubscriptionPlan, TenantCreateData, TenantUpdateData } from '@hospital/api';
import { FormLocationPicker } from '@/components/formFields';
import { emailRules } from '@/utils/formValidators';

/** 解析 JSON 字符串，失败返回默认值 */
function safeParseJson<T>(value: string | undefined | null, fallback: T): T {
  if (!value) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

const TenantFormPage: React.FC = () => {
  const { id } = useParams();
  const [_searchParams] = useSearchParams();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [_checkingCode, setCheckingCode] = useState(false);
  const cancelledRef = useRef(false);

  async function loadPlans() {
    try {
      const res = await tenantApi.getPlans(1);
      if (cancelledRef.current) return;
      setPlans(Array.isArray(res) ? res : []);
    } catch (error) {
      console.error('加载订阅计划失败:', error);
    }
  }

  async function loadTenant() {
    setLoading(true);
    try {
      const res = await tenantApi.getTenant(id);
      if (cancelledRef.current) return;
      const tenant = res;

      // 解析 JSON 字段
      const features = safeParseJson<Record<string, boolean>>(tenant.features, {});
      const branding = safeParseJson<{ logoUrl?: string; themeColor?: string }>(tenant.brandingConfig, {});
      const policy = safeParseJson<Record<string, any>>(tenant.passwordPolicy, {});
      const tags = safeParseJson<string[]>(tenant.tags, []);

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
        // 功能开关
        'features.online_payment': features.online_payment ?? false,
        'features.evaluation': features.evaluation ?? false,
        'features.waiting_queue': features.waiting_queue ?? false,
        'features.online_service': features.online_service ?? false,
        'features.miniapp_live': features.miniapp_live ?? false,
        'features.wechat_integration': features.wechat_integration ?? false,
        'features.sms_notification': features.sms_notification ?? false,
        'features.export_data': features.export_data ?? false,
        'features.api_access': features.api_access ?? false,
        'features.custom_branding': features.custom_branding ?? false,
        'features.sso': features.sso ?? false,
        // 品牌配置
        'branding.logoUrl': branding.logoUrl || '',
        'branding.themeColor': branding.themeColor || '',
        // 密码策略
        'policy.minLength': policy.min_length ?? 6,
        'policy.requireUppercase': policy.require_uppercase ?? false,
        'policy.requireDigit': policy.require_digit ?? false,
        'policy.requireSpecial': policy.require_special ?? false,
        'policy.maxLoginAttempts': policy.max_login_attempts ?? 0,
        // 限流配置
        rateLimitPerMinute: tenant.rateLimitPerMinute,
        rateLimitPerSecond: tenant.rateLimitPerSecond,
        // 运维配置
        logRetentionDays: tenant.logRetentionDays ?? 90,
        tags: tags,
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
  }

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
    // 将扁平化的表单值组装为 JSON 字符串
    const features: Record<string, boolean> = {};
    Object.keys(values).forEach((key) => {
      if (key.startsWith('features.')) {
        features[key.replace('features.', '')] = !!values[key];
      }
    });

    const brandingConfig: Record<string, string> = {};
    if (values['branding.logoUrl']) brandingConfig.logoUrl = values['branding.logoUrl'];
    if (values['branding.themeColor']) brandingConfig.themeColor = values['branding.themeColor'];

    const passwordPolicy: Record<string, any> = {
      min_length: values['policy.minLength'] ?? 6,
      require_uppercase: values['policy.requireUppercase'] ?? false,
      require_digit: values['policy.requireDigit'] ?? false,
      require_special: values['policy.requireSpecial'] ?? false,
      max_login_attempts: values['policy.maxLoginAttempts'] ?? 0,
    };

    // 清理扁平化的临时字段，只保留后端接受的字段
    const payload: Record<string, any> = {};
    const scalarFields = [
      'tenantCode', 'name', 'subscriptionPlanId', 'billingCycle',
      'maxStores', 'maxAdmins', 'maxDoctors', 'maxAppointmentsPerMonth',
      'contactName', 'contactPhone', 'contactEmail', 'address',
      'customDomain', 'subdomain', 'logRetentionDays',
      'rateLimitPerMinute', 'rateLimitPerSecond',
    ];
    scalarFields.forEach((f) => {
      if (values[f] !== undefined && values[f] !== null && values[f] !== '') {
        payload[f] = values[f];
      }
    });

    // JSON 字段
    payload.features = JSON.stringify(features);
    payload.brandingConfig = Object.keys(brandingConfig).length > 0 ? JSON.stringify(brandingConfig) : undefined;
    payload.passwordPolicy = JSON.stringify(passwordPolicy);
    if (values.tags && values.tags.length > 0) {
      payload.tags = JSON.stringify(values.tags);
    }

    try {
      if (isEdit) {
        await tenantApi.updateTenant(id, payload as TenantUpdateData);
        message.success('更新成功');
      } else {
        await tenantApi.createTenant(payload as TenantCreateData);
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
          } as any}
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
                  rules={[emailRules]}
                />
              </Col>
            </Row>
            <FormLocationPicker
              name="address"
              label="详细地址"
              mode="concatenated"
              placeholder="请输入详细地址"
            />
          </Card>

          <Card title="域名配置" size="small" style={{ marginBottom: 24 }}>
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

          <Card title="功能开关" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={[24, 0]}>
              <Col span={6}>
                <ProFormSwitch name="features.online_payment" label="在线支付" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.evaluation" label="评价功能" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.waiting_queue" label="候诊排队" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.online_service" label="在线客服" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.miniapp_live" label="小程序直播" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.wechat_integration" label="微信集成" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.sms_notification" label="短信通知" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.export_data" label="数据导出" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.api_access" label="API 开放接口" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.custom_branding" label="自定义品牌" />
              </Col>
              <Col span={6}>
                <ProFormSwitch name="features.sso" label="单点登录 (SSO)" />
              </Col>
            </Row>
          </Card>

          <Card title="品牌配置" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={12}>
                <ProFormText
                  name="branding.logoUrl"
                  label="Logo URL"
                  placeholder="请输入 Logo 图片地址"
                />
              </Col>
              <Col span={12}>
                <Space>
                  <ProFormText
                    name="branding.themeColor"
                    label="主题色"
                    placeholder="#1890ff"
                    extra="Hex 色值，如 #1890ff"
                  />
                </Space>
              </Col>
            </Row>
          </Card>

          <Card title="安全策略" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={8}>
                <ProFormDigit
                  name="policy.minLength"
                  label="密码最小长度"
                  min={4}
                  max={32}
                  initialValue={6}
                />
              </Col>
              <Col span={8}>
                <ProFormSwitch name="policy.requireUppercase" label="要求大写字母" />
              </Col>
              <Col span={8}>
                <ProFormSwitch name="policy.requireDigit" label="要求数字" />
              </Col>
              <Col span={8}>
                <ProFormSwitch name="policy.requireSpecial" label="要求特殊字符" />
              </Col>
              <Col span={8}>
                <ProFormDigit
                  name="policy.maxLoginAttempts"
                  label="登录失败锁定次数"
                  min={0}
                  extra="0 表示不锁定"
                />
              </Col>
            </Row>
          </Card>

          <Card title="限流配置" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={12}>
                <ProFormDigit
                  name="rateLimitPerMinute"
                  label="每分钟请求上限"
                  min={1}
                  max={10000}
                  placeholder="使用全局默认值 (300)"
                />
              </Col>
              <Col span={12}>
                <ProFormDigit
                  name="rateLimitPerSecond"
                  label="每秒请求上限"
                  min={1}
                  max={1000}
                  placeholder="使用全局默认值 (50)"
                />
              </Col>
            </Row>
          </Card>

          <Card title="运维配置" size="small">
            <Row gutter={24}>
              <Col span={8}>
                <ProFormDigit
                  name="logRetentionDays"
                  label="日志保留天数"
                  min={7}
                  max={365}
                  initialValue={90}
                  extra="范围 7-365 天"
                />
              </Col>
              <Col span={16}>
                <ProFormSelect
                  name="tags"
                  label="租户标签"
                  mode="tags"
                  placeholder="输入标签后回车"
                  fieldProps={{
                    tokenSeparators: [','],
                    maxTagCount: 'responsive',
                  }}
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
