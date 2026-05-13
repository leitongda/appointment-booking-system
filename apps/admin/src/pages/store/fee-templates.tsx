import { ArrowLeftOutlined, SaveOutlined, CopyOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Card, App, Table, InputNumber, Button, Spin, Space, Tag, Tooltip, Alert } from 'antd';
import { useState, useEffect } from 'react';
import { history, useParams } from '@umijs/max';
import { storeFeeTemplateApi, storeApi, consultationFeeTemplateApi } from '@hospital/api';
import type { StoreFeeTemplateWithType, Store, StoreFeeTemplateItem } from '@hospital/shared';

const StoreFeeTemplatesPage: React.FC = () => {
  const { message } = App.useApp();
  const { storeId } = useParams<{ storeId: string }>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [templates, setTemplates] = useState<StoreFeeTemplateWithType[]>([]);
  const [store, setStore] = useState<Store | null>(null);

  useEffect(() => {
    if (storeId) {
      loadData();
    }
  }, [storeId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [storeData, templateData] = await Promise.all([
        storeApi.getDetail(storeId!),
        storeFeeTemplateApi.getList(storeId!),
      ]);
      setStore(storeData);
      setTemplates(templateData);
    } catch (error: any) {
      message.error(error.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleValueChange = (index: number, field: 'initialFee' | 'followUpFee', value: number | null) => {
    const newTemplates = [...templates];
    newTemplates[index] = {
      ...newTemplates[index],
      [field]: value ?? 0,
    };
    setTemplates(newTemplates);
  };

  const handleCopyFromGlobal = (index: number) => {
    const template = templates[index];
    const newTemplates = [...templates];
    newTemplates[index] = {
      ...newTemplates[index],
      initialFee: template.globalInitialFee ?? 0,
      followUpFee: template.globalFollowUpFee ?? 0,
    };
    setTemplates(newTemplates);
    message.success('已从全局模板复制金额');
  };

  const handleCopyAllFromGlobal = () => {
    const newTemplates = templates.map(t => ({
      ...t,
      initialFee: t.globalInitialFee ?? 0,
      followUpFee: t.globalFollowUpFee ?? 0,
    }));
    setTemplates(newTemplates);
    message.success('已从全局模板复制所有金额');
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const items: StoreFeeTemplateItem[] = templates.map(t => ({
        feeTypeId: t.feeTypeId,
        feeTypeName: t.feeTypeName,
        feeTypeCode: t.feeTypeCode,
        initialFee: t.initialFee,
        followUpFee: t.followUpFee,
      }));

      await storeFeeTemplateApi.batchSave(storeId!, {
        storeId: storeId!,
        templates: items,
      });
      message.success('保存成功');
      loadData();
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '诊费类型',
      dataIndex: 'feeTypeName',
      width: 150,
      render: (text: string, record: StoreFeeTemplateWithType) => (
        <Space>
          {text}
          {record.isGlobalType ? (
            <Tag color="blue" style={{ fontSize: 10 }}>全局</Tag>
          ) : (
            <Tag color="green" style={{ fontSize: 10 }}>专属</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '类型编码',
      dataIndex: 'feeTypeCode',
      width: 120,
    },
    {
      title: (
        <Tooltip title="门店自定义的初诊金额，医生设置诊费时可一键带入">
          初诊金额
        </Tooltip>
      ),
      dataIndex: 'initialFee',
      width: 180,
      render: (_: any, record: StoreFeeTemplateWithType, index: number) => (
        <InputNumber
          value={record.initialFee}
          min={0}
          precision={2}
          addonAfter="元"
          style={{ width: 140 }}
          onChange={(value) => handleValueChange(index, 'initialFee', value)}
        />
      ),
    },
    {
      title: (
        <Tooltip title="门店自定义的复诊金额，医生设置诊费时可一键带入">
          复诊金额
        </Tooltip>
      ),
      dataIndex: 'followUpFee',
      width: 180,
      render: (_: any, record: StoreFeeTemplateWithType, index: number) => (
        <InputNumber
          value={record.followUpFee}
          min={0}
          precision={2}
          addonAfter="元"
          style={{ width: 140 }}
          onChange={(value) => handleValueChange(index, 'followUpFee', value)}
        />
      ),
    },
    {
      title: (
        <Tooltip title="全局默认模板金额，仅供参考">
          全局模板参考
        </Tooltip>
      ),
      key: 'globalRef',
      width: 200,
      render: (_: any, record: StoreFeeTemplateWithType) => (
        <span style={{ color: '#999' }}>
          初诊: ¥{Number(record.globalInitialFee || 0).toFixed(2)} / 
          复诊: ¥{Number(record.globalFollowUpFee || 0).toFixed(2)}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: StoreFeeTemplateWithType, index: number) => (
        <Tooltip title="复制全局模板金额到门店模板">
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopyFromGlobal(index)}
          >
            复制全局
          </Button>
        </Tooltip>
      ),
    },
  ];

  return (
    <PageContainer
      header={{
        title: `${store?.name || '门店'} - 诊费模板配置`,
        breadcrumb: {
          items: [
            { title: '门店管理' },
            { title: '门店列表', href: '/organization/store/list' },
            { title: '诊费模板' },
          ],
        },
      }}
      extra={
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => history.push('/organization/store/list')}>
            返回门店列表
          </Button>
          <Button onClick={() => history.push(`/organization/store/${storeId}/fee-types`)}>
            管理诊费类型
          </Button>
        </Space>
      }
    >
      <Card>
        <Alert
          title="门店诊费模板说明"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>门店诊费模板用于为该门店的医生提供默认诊费金额</li>
              <li>医生设置诊费时，可以一键带入门店模板中的金额</li>
              <li>如果门店未配置某个诊费类型的模板，医生一键带入时会使用全局模板的金额</li>
              <li>门店可以创建专属的诊费类型，请点击"管理诊费类型"按钮</li>
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Spin spinning={loading}>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <Space>
              <Button icon={<CopyOutlined />} onClick={handleCopyAllFromGlobal}>
                全部复制自全局模板
              </Button>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
                保存
              </Button>
            </Space>
          </div>

          <Table
            columns={columns}
            dataSource={templates}
            rowKey="feeTypeId"
            pagination={false}
            size="middle"
          />

          {templates.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              暂无诊费类型，请先到配置中心 - 诊费类型添加全局诊费类型，或点击"管理诊费类型"创建门店专属类型
            </div>
          )}
        </Spin>
      </Card>
    </PageContainer>
  );
};

export default StoreFeeTemplatesPage;

