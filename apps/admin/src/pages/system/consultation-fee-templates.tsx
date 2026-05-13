import { PageContainer } from '@ant-design/pro-components';
import { Card, App, Table, InputNumber, Button, Spin, Alert } from 'antd';
import { useState, useEffect } from 'react';
import { useAccess } from '@umijs/max';
import { consultationFeeTemplateApi } from '@hospital/api';
import type { ConsultationFeeTemplateWithType } from '@hospital/shared';

const ConsultationFeeTemplatesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [templates, setTemplates] = useState<ConsultationFeeTemplateWithType[]>([]);
  const canEdit = access.hasPermission('system:consultation-fee');

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const data = await consultationFeeTemplateApi.getList();
      setTemplates(data);
    } catch (error: any) {
      message.error(error.message || '加载诊费模板失败');
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

  const handleSave = async () => {
    setSaving(true);
    try {
      await consultationFeeTemplateApi.batchUpdate(
        templates.map(t => ({
          feeTypeId: t.feeTypeId,
          initialFee: t.initialFee,
          followUpFee: t.followUpFee,
          status: t.status,
        }))
      );
      message.success('保存成功');
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
    },
    {
      title: '类型编码',
      dataIndex: 'feeTypeCode',
      width: 150,
    },
    {
      title: '初诊金额',
      dataIndex: 'initialFee',
      width: 180,
      render: (_: any, record: ConsultationFeeTemplateWithType, index: number) => (
        <InputNumber
          value={record.initialFee}
          min={0}
          precision={2}
          addonAfter="元"
          style={{ width: 150 }}
          onChange={(value) => handleValueChange(index, 'initialFee', value)}
          disabled={!canEdit}
        />
      ),
    },
    {
      title: '复诊金额',
      dataIndex: 'followUpFee',
      width: 180,
      render: (_: any, record: ConsultationFeeTemplateWithType, index: number) => (
        <InputNumber
          value={record.followUpFee}
          min={0}
          precision={2}
          addonAfter="元"
          style={{ width: 150 }}
          onChange={(value) => handleValueChange(index, 'followUpFee', value)}
          disabled={!canEdit}
        />
      ),
    },
  ];

  return (
    <PageContainer>
      <Card>
        <Alert
          title="全局诊费模板说明"
          description="此处配置的诊费模板为全局默认模板。当医生开启「使用诊费模板」选项时，将自动应用此模板的诊费设置到该医生的所有门店和科室。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Spin spinning={loading}>
          <Table
            rowKey="feeTypeId"
            columns={columns}
            dataSource={templates}
            pagination={false}
            bordered
          />
          {canEdit && (
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Button type="primary" onClick={handleSave} loading={saving}>
                保存模板
              </Button>
            </div>
          )}
        </Spin>
      </Card>
    </PageContainer>
  );
};

export default ConsultationFeeTemplatesPage;
