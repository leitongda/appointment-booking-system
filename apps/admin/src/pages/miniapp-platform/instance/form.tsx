import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col, Divider, Radio, Tag } from 'antd';
import { history, useParams, useSearchParams } from '@umijs/max';
import { useEffect, useState } from 'react';
import { miniappPlatformApi, storeApi } from '@hospital/api';
import type { MiniappInstanceCreateData, MiniappInstanceUpdateData } from '@hospital/api';

const TEMPLATE_LIST = [
  {
    code: 'modern-general',
    name: '现代综合医疗',
    description: '适用于综合医院，提供完整的预约挂号、在线问诊、健康档案等功能',
    color: '#4D7CB8',
    category: '综合医疗',
    features: ['在线预约', '在线问诊', '健康档案', '报告查询'],
  },
  {
    code: 'elderly-tcm',
    name: '长辈友好/中医康养',
    description: '大字体设计，简洁操作流程，专注于中医诊疗和康养服务',
    color: '#8B6F47',
    category: '长辈友好',
    features: ['大字体设计', '中医诊疗', '康养服务', '简单操作'],
  },
  {
    code: 'premium-specialty',
    name: '高端专科门诊',
    description: '简约大气设计，适用于高端专科诊所，提供VIP服务体验',
    color: '#8B7355',
    category: '专科门诊',
    features: ['VIP服务', '专科诊疗', '预约管理', '会员体系'],
  },
  {
    code: 'family-pediatrics',
    name: '亲子儿科',
    description: '温馨可爱风格，专注于儿科诊疗，支持家属关联和儿童健康管理',
    color: '#5B9BD5',
    category: '儿科',
    features: ['儿童健康', '家属关联', '疫苗提醒', '成长记录'],
  },
  {
    code: 'womens-health',
    name: '女性健康',
    description: '优雅柔和设计，专注于女性健康管理，提供妇科和产后康复服务',
    color: '#C4908D',
    category: '女性健康',
    features: ['女性健康', '妇科服务', '产后康复', '健康咨询'],
  },
];

const InstanceFormPage: React.FC = () => {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [stores, setStores] = useState<any[]>([]);
  const [paymentProfiles, setPaymentProfiles] = useState<any[]>([]);
  const [_checkingCode, setCheckingCode] = useState(false);
  const [_checkingAppId, setCheckingAppId] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string | undefined>(
    searchParams.get('template') || undefined
  );

  async function loadStores() {
    try {
      const res = await storeApi.getList({ page: 1, pageSize: 100 });
      setStores((res as any).data || []);
    } catch (error) {
      console.error('加载门店列表失败:', error);
    }
  }

  async function loadPaymentProfiles() {
    try {
      const res = await miniappPlatformApi.getPaymentProfiles({ page: 1, pageSize: 100 });
      setPaymentProfiles((res as any).data || []);
    } catch (error) {
      console.error('加载支付配置失败:', error);
    }
  }

  async function loadInstance() {
    setLoading(true);
    try {
      const instance = await miniappPlatformApi.getMiniappInstance(id!);
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
  }

  useEffect(() => {
    loadStores();
    loadPaymentProfiles();
    if (isEdit) {
      loadInstance();
    } else if (selectedTemplate) {
      form.setFieldValue('templateId', selectedTemplate);
    }
  }, [id]);

  const checkCode = async (_: any, value: string) => {
    if (!value) return Promise.resolve();

    // 编辑模式下，如果 code 没有变化，不需要检查
    if (isEdit) {
      const currentCode = form.getFieldValue('code');
      if (currentCode === value) return Promise.resolve();
    }

    setCheckingCode(true);
    try {
      const res = await miniappPlatformApi.checkInstanceUnique(value, undefined, isEdit ? id : undefined);
      if ((res as any).code_exists) {
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
      if ((res as any).app_id_exists) {
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
      history.push('/platform/miniapp-platform/instance');
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
          } as any}
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

          {!isEdit && (
            <>
              <Form.Item label="选择模板" name="templateId" rules={[{ required: true, message: '请选择模板' }]}>
                <Radio.Group
                  value={selectedTemplate}
                  onChange={(e) => {
                    setSelectedTemplate(e.target.value);
                    form.setFieldValue('templateId', e.target.value);
                  }}
                  style={{ width: '100%' }}
                >
                  <Row gutter={[16, 16]}>
                    {TEMPLATE_LIST.map((template) => (
                      <Col key={template.code} span={8}>
                        <Radio value={template.code} style={{ display: 'none' }} />
                        <Card
                          hoverable
                          onClick={() => {
                            setSelectedTemplate(template.code);
                            form.setFieldValue('templateId', template.code);
                          }}
                          style={{
                            height: '100%',
                            border: selectedTemplate === template.code ? '2px solid #1890ff' : '1px solid #d9d9d9',
                            cursor: 'pointer',
                          }}
                          styles={{ body: { padding: '12px' } }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              marginBottom: 8,
                            }}
                          >
                            <div
                              style={{
                                width: 40,
                                height: 40,
                                background: template.color,
                                borderRadius: 4,
                                marginRight: 12,
                              }}
                            />
                            <div style={{ flex: 1 }}>
                              <div style={{ fontWeight: 'bold', fontSize: 14 }}>{template.name}</div>
                              <Tag color="blue">{template.category}</Tag>
                            </div>
                            {selectedTemplate === template.code && (
                              <div style={{ color: '#1890ff', fontSize: 18 }}>✓</div>
                            )}
                          </div>
                          <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                            {template.description}
                          </div>
                          <div>
                            {template.features?.slice(0, 3).map((feature, index) => (
                              <Tag key={index} style={{ fontSize: 11, marginBottom: 4 }}>
                                {feature}
                              </Tag>
                            ))}
                          </div>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Radio.Group>
              </Form.Item>
              {selectedTemplate && (
                <Form.Item label="">
                  <Card size="small" style={{ background: '#f0f5ff' }}>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <strong>已选模板：</strong>
                      {TEMPLATE_LIST.find(t => t.code === selectedTemplate)?.name}
                    </div>
                  </Card>
                </Form.Item>
              )}
            </>
          )}

          {isEdit && (
            <Row gutter={24}>
              <Col span={12}>
                <ProFormSelect
                  name="templateId"
                  label="模板"
                  options={TEMPLATE_LIST.map(t => ({ label: t.name, value: t.code }))}
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
          )}

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
