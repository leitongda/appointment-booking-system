import { ProFormText, ProFormSelect, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Card, Row, Col, Space, message } from 'antd';
import { history, useParams, useAccess } from '@umijs/max';
import { useEffect, useRef, useState } from 'react';
import type { ProFormInstance } from '@ant-design/pro-components';
import { tenantApi } from '@hospital/api';
import type { SubscriptionPlan, TenantCreateData, TenantUpdateData, TenantSelfUpdateData } from '@hospital/api';
import FormPage from '@/components/FormPage';
import { FormLocationPicker } from '@/components/formFields';
import { useFieldUnique } from '@/hooks/useUniqueValidation';
import { requiredRules, patternRules, stringLengthRules, emailRules } from '@/utils/formValidators';

/** 解析 JSON 字符串，失败返回默认值 */
function safeParseJson<T>(value: string | undefined | null, fallback: T): T {
  if (!value) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

/** 将后端租户数据转换为表单初始值（JSON 字段扁平化） */
function tenantToFormValues(tenant: Record<string, any>): Record<string, any> {
  const features = safeParseJson<Record<string, boolean>>(tenant.features, {});
  const branding = safeParseJson<{ logoUrl?: string; themeColor?: string }>(tenant.brandingConfig, {});
  const policy = safeParseJson<Record<string, any>>(tenant.passwordPolicy, {});
  const tags = safeParseJson<string[]>(tenant.tags, []);

  return {
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
    'features.basic_appointment': features.basic_appointment ?? false,
    'features.basic_schedule': features.basic_schedule ?? false,
    'features.basic_statistics': features.basic_statistics ?? false,
    'features.advanced_statistics': features.advanced_statistics ?? false,
    'features.wechat_integration': features.wechat_integration ?? false,
    'features.sms_notification': features.sms_notification ?? false,
    'features.export_data': features.export_data ?? false,
    'features.api_access': features.api_access ?? false,
    'features.custom_branding': features.custom_branding ?? false,
    'features.priority_support': features.priority_support ?? false,
    'features.sso': features.sso ?? false,
    'features.online_payment': features.online_payment ?? false,
    'features.evaluation': features.evaluation ?? false,
    'features.waiting_queue': features.waiting_queue ?? false,
    'features.online_service': features.online_service ?? false,
    'features.miniapp_live': features.miniapp_live ?? false,
    'features.beta_features': features.beta_features ?? false,
    'features.beta_ai_assistant': features.beta_ai_assistant ?? false,
    'features.beta_analytics_v2': features.beta_analytics_v2 ?? false,
    // 品牌配置
    'branding.logoUrl': branding.logoUrl || '',
    'branding.themeColor': branding.themeColor || '',
    // 密码策略
    'policy.minLength': policy.min_length ?? 6,
    'policy.maxLength': policy.max_length ?? 20,
    'policy.requireUppercase': policy.require_uppercase ?? false,
    'policy.requireLowercase': policy.require_lowercase ?? false,
    'policy.requireDigit': policy.require_digit ?? false,
    'policy.requireSpecial': policy.require_special ?? false,
    'policy.disallowUsername': policy.disallow_username ?? false,
    'policy.disallowPhone': policy.disallow_phone ?? false,
    'policy.maxRepeatedChars': policy.max_repeated_chars ?? 0,
    'policy.historyCount': policy.history_count ?? 0,
    'policy.expiryDays': policy.expiry_days ?? 0,
    // 限流配置
    rateLimitPerMinute: tenant.rateLimitPerMinute,
    rateLimitPerSecond: tenant.rateLimitPerSecond,
    // 运维配置
    logRetentionDays: tenant.logRetentionDays ?? 90,
    tags: tags,
  };
}

/** 将表单值组装为后端 payload（JSON 字段序列化） */
function buildPayload(values: Record<string, any>, isEdit: boolean): Record<string, any> {
  // 功能开关
  const features: Record<string, boolean> = {};
  Object.keys(values).forEach((key) => {
    if (key.startsWith('features.')) {
      features[key.replace('features.', '')] = !!values[key];
    }
  });

  // 品牌配置
  const brandingConfig: Record<string, string> = {};
  if (values['branding.logoUrl']) brandingConfig.logoUrl = values['branding.logoUrl'];
  if (values['branding.themeColor']) brandingConfig.themeColor = values['branding.themeColor'];

  // 密码策略
  const passwordPolicy: Record<string, any> = {
    min_length: values['policy.minLength'] ?? 6,
    max_length: values['policy.maxLength'] ?? 20,
    require_uppercase: values['policy.requireUppercase'] ?? false,
    require_lowercase: values['policy.requireLowercase'] ?? false,
    require_digit: values['policy.requireDigit'] ?? false,
    require_special: values['policy.requireSpecial'] ?? false,
    disallow_username: values['policy.disallowUsername'] ?? false,
    disallow_phone: values['policy.disallowPhone'] ?? false,
    max_repeated_chars: values['policy.maxRepeatedChars'] ?? 0,
    history_count: values['policy.historyCount'] ?? 0,
    expiry_days: values['policy.expiryDays'] ?? 0,
  };

  // 标量字段
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

  if (!isEdit && values.isTrial) {
    payload.isTrial = true;
  }

  if (Object.keys(features).length > 0) {
    payload.features = JSON.stringify(features);
  }
  payload.brandingConfig = Object.keys(brandingConfig).length > 0 ? JSON.stringify(brandingConfig) : undefined;
  payload.passwordPolicy = JSON.stringify(passwordPolicy);
  if (values.tags && values.tags.length > 0) {
    payload.tags = JSON.stringify(values.tags);
  }

  return payload;
}

const TenantFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const access = useAccess();
  const isPlatformAdmin = access.canSuperAdmin;
  const formRef = useRef<ProFormInstance>() as React.RefObject<ProFormInstance>;
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialValues, setInitialValues] = useState<Record<string, any> | undefined>(undefined);
  const cancelledRef = useRef(false);

  const { rule: tenantCodeUniqueRule } = useFieldUnique({
    checkFn: (value, excludeId) =>
      tenantApi.checkTenantCodeUnique(value, excludeId as string | undefined).then(r => ({ isUnique: !r.exists })),
    message: '该租户标识已存在',
    excludeId: isEdit ? id : undefined,
  });

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
      setInitialValues(tenantToFormValues(res));
    } catch (error) {
      if (cancelledRef.current) return;
      setInitialValues(undefined);
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

  const handleSubmit = async (values: any) => {
    const payload = buildPayload(values, isEdit);

    try {
      if (isEdit) {
        if (isPlatformAdmin) {
          await tenantApi.updateTenant(id, payload as TenantUpdateData);
        } else {
          const selfPayload: Record<string, any> = {};
          const selfFields = ['name', 'contactName', 'contactPhone', 'contactEmail', 'address'];
          selfFields.forEach((f) => {
            if (values[f] !== undefined && values[f] !== null && values[f] !== '') {
              selfPayload[f] = values[f];
            }
          });
          const brandingConfig: Record<string, string> = {};
          if (values['branding.logoUrl']) brandingConfig.logoUrl = values['branding.logoUrl'];
          if (values['branding.themeColor']) brandingConfig.themeColor = values['branding.themeColor'];
          if (Object.keys(brandingConfig).length > 0) {
            selfPayload.brandingConfig = JSON.stringify(brandingConfig);
          }
          await tenantApi.updateTenantSelf(id, selfPayload as TenantSelfUpdateData);
        }
      } else {
        await tenantApi.createTenant(payload as TenantCreateData);
      }
      history.push('/platform/tenant');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <FormPage
      title={isEdit ? '编辑租户' : '新增租户'}
      formRef={formRef}
      loading={loading}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
      formProps={{
        validateMessages: { required: '此项为必填项' },
      }}
    >
      <Card title="基础信息" style={{ marginBottom: 16 }}>
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
                      requiredRules('请输入租户标识'),
                      stringLengthRules(3, 50),
                      patternRules(/^[a-z0-9-]+$/, '只能包含小写字母、数字和连字符'),
                      tenantCodeUniqueRule,
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
              rules={[requiredRules('请输入租户名称')]}
            />
          </Col>
        </Row>
        <Row gutter={24} hidden={!isPlatformAdmin}>
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
        <Row gutter={24} hidden={!isPlatformAdmin}>
          <Col span={12}>
            <ProFormSwitch
              name="isTrial"
              label="试用租户"
              extra="试用租户自动获得试用状态和有效期"
              hidden={isEdit}
            />
          </Col>
        </Row>
      </Card>

      <Card title="配额设置" size="small" style={{ marginBottom: 16 }} hidden={!isPlatformAdmin}>
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

      <Card title="联系信息" size="small" style={{ marginBottom: 16 }}>
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

      <Card title="域名配置" size="small" style={{ marginBottom: 16 }} hidden={!isPlatformAdmin}>
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

      <Card title="功能开关" size="small" style={{ marginBottom: 16 }} hidden={!isPlatformAdmin}>
        <Row gutter={[24, 0]}>
          <Col span={6}>
            <ProFormSwitch name="features.basic_appointment" label="基础预约" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.basic_schedule" label="基础排班" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.basic_statistics" label="基础统计" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.advanced_statistics" label="高级数据分析" />
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
            <ProFormSwitch name="features.priority_support" label="优先技术支持" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.sso" label="单点登录 (SSO)" />
          </Col>
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
          <Col span={24}>
            <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>实验性功能</div>
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.beta_features" label="灰度功能总开关" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.beta_ai_assistant" label="AI 辅助 (实验性)" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="features.beta_analytics_v2" label="新版数据分析 (实验性)" />
          </Col>
        </Row>
      </Card>

      <Card title="品牌配置" size="small" style={{ marginBottom: 16 }}>
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
                placeholder="#1677ff"
                extra="Hex 色值，如 #1677ff"
              />
            </Space>
          </Col>
        </Row>
      </Card>

      <Card title="安全策略" size="small" style={{ marginBottom: 16 }} hidden={!isPlatformAdmin}>
        <Row gutter={24}>
          <Col span={6}>
            <ProFormDigit
              name="policy.minLength"
              label="密码最小长度"
              min={4}
              max={32}
              initialValue={6}
            />
          </Col>
          <Col span={6}>
            <ProFormDigit
              name="policy.maxLength"
              label="密码最大长度"
              min={8}
              max={64}
              initialValue={20}
            />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="policy.requireUppercase" label="要求大写字母" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="policy.requireLowercase" label="要求小写字母" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="policy.requireDigit" label="要求数字" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="policy.requireSpecial" label="要求特殊字符" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="policy.disallowUsername" label="禁止包含用户名" />
          </Col>
          <Col span={6}>
            <ProFormSwitch name="policy.disallowPhone" label="禁止包含手机号" />
          </Col>
          <Col span={6}>
            <ProFormDigit
              name="policy.maxRepeatedChars"
              label="最大连续重复字符"
              min={0}
              max={10}
              extra="0 表示不限制"
            />
          </Col>
          <Col span={6}>
            <ProFormDigit
              name="policy.historyCount"
              label="密码历史检查"
              min={0}
              max={10}
              extra="0 表示不检查"
            />
          </Col>
          <Col span={6}>
            <ProFormDigit
              name="policy.expiryDays"
              label="密码过期天数"
              min={0}
              max={365}
              extra="0 表示不过期"
            />
          </Col>
        </Row>
      </Card>

      <Card title="限流配置" size="small" style={{ marginBottom: 16 }} hidden={!isPlatformAdmin}>
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

      <Card title="运维配置" size="small" hidden={!isPlatformAdmin}>
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
    </FormPage>
  );
};

export default TenantFormPage;
