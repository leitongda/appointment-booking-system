import { PageContainer } from '@ant-design/pro-components';
import { Card, Form, InputNumber, Select, Switch, Button, Space, Alert, App } from 'antd';
import { useParams, history } from '@umijs/max';
import { useEffect, useState } from 'react';
import { storeApi, storeVisitTypeConfigApi } from '@hospital/api';
import type { Store, TimeUnit, VisitScope } from '@hospital/shared';
import { TIME_UNIT_OPTIONS, VISIT_SCOPE_OPTIONS } from '@hospital/shared';

const VisitTypeConfigPage = () => {
  const { message } = App.useApp();
  const { storeId } = useParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [store, setStore] = useState<Store | null>(null);

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      if (!storeId) return;
      
      setLoading(true);
      try {
        // 加载门店信息
        const storeData = await storeApi.getDetail(storeId);
        setStore(storeData);

        // 加载配置
        const configResult = await storeVisitTypeConfigApi.getByStoreId(storeId);
        const configData = configResult.data;

        // 设置表单值
        form.setFieldsValue({
          timeLimit: configData.timeLimit || 30,
          timeUnit: configData.timeUnit || 'days',
          scope: configData.scope || 'same_doctor',
          status: configData.status === 1,
        });
      } catch (error) {
        console.error('加载数据失败:', error);
        message.error('加载数据失败');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [storeId, form, message]);

  // 保存配置
  const handleSave = async (values: any) => {
    if (!storeId) return;

    setSaving(true);
    try {
      await storeVisitTypeConfigApi.update(storeId, {
        timeLimit: values.timeLimit,
        timeUnit: values.timeUnit as TimeUnit,
        scope: values.scope as VisitScope,
        status: values.status ? 1 : 0,
      });
      message.success('保存成功');
    } catch (error) {
      console.error('保存失败:', error);
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 恢复默认
  const handleReset = async () => {
    if (!storeId) return;

    try {
      await storeVisitTypeConfigApi.delete(storeId);
      message.success('已恢复默认配置');
      // 重新加载
      form.setFieldsValue({
        timeLimit: 30,
        timeUnit: 'days',
        scope: 'same_doctor',
        status: true,
      });
    } catch (error) {
      console.error('重置失败:', error);
      message.error('重置失败');
    }
  };

  return (
    <PageContainer
      title={`${store?.name || '门店'} - 复诊规则配置`}
      breadcrumb={{
        items: [
          { title: <a onClick={() => history.push('/organization/store')}>门店管理</a> },
          { title: '复诊规则配置' },
        ],
      }}
    >
      <Card loading={loading}>
        <Alert
          title="复诊规则说明"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>复诊规则用于判断患者预约时是初诊还是复诊，从而确定诊费金额</li>
              <li><strong>时间限制</strong>：患者在指定时间内再次预约，视为复诊</li>
              <li><strong>复诊范围</strong>：指定判断复诊的范围（同一医生、同一科室或同一门店）</li>
              <li>如果关闭此功能，所有预约将按初诊计费</li>
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            timeLimit: 30,
            timeUnit: 'days',
            scope: 'same_doctor',
            status: true,
          }}
        >
          <Form.Item
            name="status"
            label="启用复诊规则"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="关闭" />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.status !== cur.status}>
            {({ getFieldValue }) => {
              const isEnabled = getFieldValue('status');
              return (
                <div style={{ opacity: isEnabled ? 1 : 0.5, pointerEvents: isEnabled ? 'auto' : 'none' }}>
                  <Form.Item
                    label="复诊时间限制"
                    required
                    style={{ marginBottom: 0 }}
                  >
                    <Space>
                      <Form.Item
                        name="timeLimit"
                        noStyle
                        rules={[{ required: true, message: '请输入时间限制' }]}
                      >
                        <InputNumber min={1} max={365} style={{ width: 100 }} />
                      </Form.Item>
                      <Form.Item
                        name="timeUnit"
                        noStyle
                        rules={[{ required: true, message: '请选择时间单位' }]}
                      >
                        <Select style={{ width: 100 }} options={TIME_UNIT_OPTIONS} />
                      </Form.Item>
                      <span style={{ color: '#999' }}>内再次预约视为复诊</span>
                    </Space>
                  </Form.Item>

                  <Form.Item
                    name="scope"
                    label="复诊范围"
                    rules={[{ required: true, message: '请选择复诊范围' }]}
                    style={{ marginTop: 24 }}
                    extra="选择判断复诊的范围条件"
                  >
                    <Select style={{ width: 300 }} options={VISIT_SCOPE_OPTIONS} />
                  </Form.Item>
                </div>
              );
            }}
          </Form.Item>

          <Form.Item style={{ marginTop: 32 }}>
            <Space>
              <Button type="primary" htmlType="submit" loading={saving}>
                保存配置
              </Button>
              <Button onClick={handleReset}>
                恢复默认
              </Button>
              <Button onClick={() => history.push('/organization/store')}>
                返回
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </PageContainer>
  );
};

export default VisitTypeConfigPage;

