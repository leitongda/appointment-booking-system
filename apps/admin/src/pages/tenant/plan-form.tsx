import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormDigit, ProFormTextArea, ProFormSwitch, ProFormSelect } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col, InputNumber } from 'antd';
import { history, useParams } from '@umijs/max';
import { useEffect, useState } from 'react';
import { tenantApi } from '@hospital/api';
import type { SubscriptionPlanCreateData, SubscriptionPlanUpdateData, SubscriptionPlan } from '@hospital/api';

const SubscriptionPlanFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit) {
      loadPlan();
    }
  }, [id]);

  const loadPlan = async () => {
    setLoading(true);
    try {
      const res = await tenantApi.getPlan(id);
      const plan = res.data;
      form.setFieldsValue({
        planCode: plan.planCode,
        name: plan.name,
        description: plan.description,
        priceMonthly: plan.priceMonthly,
        priceYearly: plan.priceYearly,
        currency: plan.currency,
        maxStores: plan.maxStores,
        maxAdmins: plan.maxAdmins,
        maxDoctors: plan.maxDoctors,
        maxAppointmentsPerMonth: plan.maxAppointmentsPerMonth,
        maxStorageMb: plan.maxStorageMb,
        features: plan.features,
        status: plan.status,
        sortOrder: plan.sortOrder,
        isDefault: plan.isDefault,
      });
    } catch (error) {
      message.error('加载订阅计划失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (isEdit) {
        await tenantApi.updatePlan(id, values as SubscriptionPlanUpdateData);
        message.success('更新成功');
      } else {
        await tenantApi.createPlan(values as SubscriptionPlanCreateData);
        message.success('创建成功');
      }
      history.push('/tenant/plans');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <PageContainer title={isEdit ? '编辑订阅计划' : '新增订阅计划'}>
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
            <Col span={8}>
              <ProFormText
                name="planCode"
                label="计划编码"
                placeholder="例如: basic, pro, enterprise"
                rules={[
                  { required: true, message: '请输入计划编码' },
                  { pattern: /^[a-z0-9-]+$/, message: '只能包含小写字母、数字和连字符' },
                ]}
                disabled={isEdit}
              />
            </Col>
            <Col span={8}>
              <ProFormText
                name="name"
                label="计划名称"
                placeholder="例如: 基础版, 专业版, 企业版"
                rules={[{ required: true, message: '请输入计划名称' }]}
              />
            </Col>
            <Col span={8}>
              <ProFormSelect
                name="status"
                label="状态"
                options={[
                  { label: '启用', value: 1 },
                  { label: '禁用', value: 0 },
                ]}
                initialValue={1}
              />
            </Col>
          </Row>

          <ProFormTextArea
            name="description"
            label="计划描述"
            placeholder="请输入计划描述"
            rows={2}
          />

          <Card title="价格设置" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={8}>
                <ProFormDigit
                  name="priceMonthly"
                  label="月付价格"
                  min={0}
                  precision={2}
                  initialValue={0}
                  fieldProps={{
                    prefix: '¥',
                  }}
                />
              </Col>
              <Col span={8}>
                <ProFormDigit
                  name="priceYearly"
                  label="年付价格"
                  min={0}
                  precision={2}
                  initialValue={0}
                  fieldProps={{
                    prefix: '¥',
                  }}
                />
              </Col>
              <Col span={8}>
                <ProFormSelect
                  name="currency"
                  label="货币单位"
                  options={[
                    { label: '人民币 (CNY)', value: 'CNY' },
                    { label: '美元 (USD)', value: 'USD' },
                  ]}
                  initialValue="CNY"
                />
              </Col>
            </Row>
          </Card>

          <Card title="配额限制" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={24}>
              <Col span={6}>
                <ProFormDigit
                  name="maxStores"
                  label="最大门店数"
                  min={1}
                  initialValue={1}
                  fieldProps={{ style: { width: '100%' } }}
                />
              </Col>
              <Col span={6}>
                <ProFormDigit
                  name="maxAdmins"
                  label="最大管理员数"
                  min={1}
                  initialValue={5}
                  fieldProps={{ style: { width: '100%' } }}
                />
              </Col>
              <Col span={6}>
                <ProFormDigit
                  name="maxDoctors"
                  label="最大医生数"
                  min={1}
                  initialValue={50}
                  fieldProps={{ style: { width: '100%' } }}
                />
              </Col>
              <Col span={6}>
                <ProFormDigit
                  name="maxAppointmentsPerMonth"
                  label="月预约上限"
                  min={1}
                  initialValue={1000}
                  fieldProps={{ style: { width: '100%' } }}
                />
              </Col>
            </Row>
            <Row gutter={24}>
              <Col span={6}>
                <ProFormDigit
                  name="maxStorageMb"
                  label="存储空间上限 (MB)"
                  min={1}
                  initialValue={1024}
                  fieldProps={{ style: { width: '100%' } }}
                />
              </Col>
            </Row>
          </Card>

          <Card title="功能配置" size="small" style={{ marginBottom: 24 }}>
            <ProFormTextArea
              name="features"
              label="功能开关配置 (JSON)"
              placeholder='{"basic_appointment": true, "advanced_statistics": true}'
              rows={4}
              extra="JSON 格式的功能开关配置"
              rules={[
                {
                  validator: (_, value) => {
                    if (!value) return Promise.resolve();
                    try {
                      JSON.parse(value);
                      return Promise.resolve();
                    } catch {
                      return Promise.reject(new Error('请输入有效的 JSON 格式'));
                    }
                  },
                },
              ]}
            />
          </Card>

          <Row gutter={24}>
            <Col span={8}>
              <ProFormDigit
                name="sortOrder"
                label="排序"
                min={0}
                initialValue={0}
                extra="数值越小越靠前"
              />
            </Col>
            <Col span={8}>
              <ProFormSwitch
                name="isDefault"
                label="设为默认"
                extra="新租户默认使用此计划"
              />
            </Col>
          </Row>
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default SubscriptionPlanFormPage;
