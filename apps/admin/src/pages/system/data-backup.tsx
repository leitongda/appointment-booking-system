import { useState, useEffect } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import {
  Card,
  Row,
  Col,
  Button,
  Select,
  Upload,
  Modal,
  Alert,
  Typography,
  Space,
  Divider,
  Spin,
  Result,
} from 'antd';
import {
  DownloadOutlined,
  UploadOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { backupApi, tenantApi } from '@hospital/api';
import type { BackupPrecheckResult } from '@hospital/api';
import { useListPage } from '@/hooks/useListPage';

const { Text } = Typography;

const DataBackupPage: React.FC = () => {
  const { message } = useListPage();
  const [tenantOptions, setTenantOptions] = useState<{ label: string; value: string }[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>('');
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [precheckResult, setPrecheckResult] = useState<BackupPrecheckResult | null>(null);
  const [precheckFile, setPrecheckFile] = useState<File | null>(null);
  const [importVisible, setImportVisible] = useState(false);

  // 加载租户列表
  useEffect(() => {
    tenantApi
      .getTenants({ pageSize: 200 })
      .then((res: any) => {
        const list = res.data || res.items || res || [];
        setTenantOptions(list.map((t: any) => ({ label: t.name, value: t.id })));
      })
      .catch(() => {
        message.warning('加载租户列表失败');
      });
  }, []);

  // 导出
  const handleExport = async () => {
    if (!selectedTenant) {
      message.warning('请先选择租户');
      return;
    }
    setExporting(true);
    try {
      const blob = (await backupApi.exportData(selectedTenant)) as any;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `backup-${selectedTenant}-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (e: any) {
      message.error(e?.message || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  // 预检
  const handlePrecheck = async (file: File) => {
    if (!selectedTenant) {
      message.warning('请先选择租户');
      return;
    }
    setImporting(true);
    try {
      const result = await backupApi.precheck(selectedTenant, file);
      setPrecheckResult(result);
      setPrecheckFile(file);
      setImportVisible(true);
    } catch (e: any) {
      message.error(e?.message || '预检失败');
    } finally {
      setImporting(false);
    }
  };

  // 确认导入
  const handleImport = async (overwrite: boolean) => {
    if (!precheckFile || !selectedTenant) return;
    setImporting(true);
    try {
      await backupApi.importData(selectedTenant, precheckFile, overwrite);
      message.success('数据恢复成功');
      setImportVisible(false);
      setPrecheckResult(null);
      setPrecheckFile(null);
    } catch (e: any) {
      message.error(e?.message || '导入失败');
    } finally {
      setImporting(false);
    }
  };

  return (
    <PageContainer
      title="数据备份"
      content="导出租户数据备份文件，或从备份文件恢复数据。仅平台管理员可操作。"
    >
      <Row gutter={24}>
        {/* 左侧：操作区 */}
        <Col span={12}>
          <Card title="选择租户" style={{ marginBottom: 24 }}>
            <Select
              placeholder="请选择租户"
              options={tenantOptions}
              value={selectedTenant || undefined}
              onChange={setSelectedTenant}
              style={{ width: '100%' }}
              showSearch
              optionFilterProp="label"
            />
          </Card>

          <Card title="导出备份" style={{ marginBottom: 24 }}>
            <Text type="secondary">
              将选中租户的所有业务数据导出为 JSON 文件。
            </Text>
            <div style={{ marginTop: 16 }}>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={exporting}
                disabled={!selectedTenant}
                onClick={handleExport}
              >
                导出数据
              </Button>
            </div>
          </Card>

          <Card title="恢复数据">
            <Alert
              message="恢复操作将覆盖现有数据"
              description="请先通过预检确认备份文件内容，再决定是否覆盖。"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Upload
              accept=".json"
              showUploadList={false}
              beforeUpload={(file) => {
                handlePrecheck(file);
                return false;
              }}
              disabled={!selectedTenant || importing}
            >
              <Button
                icon={<UploadOutlined />}
                loading={importing}
                disabled={!selectedTenant}
              >
                选择备份文件
              </Button>
            </Upload>
          </Card>
        </Col>

        {/* 右侧：说明 */}
        <Col span={12}>
          <Card title="操作说明">
            <div style={{ lineHeight: 2 }}>
              <p><strong>导出：</strong></p>
              <ul>
                <li>选择目标租户，点击"导出数据"</li>
                <li>系统将生成 JSON 格式的备份文件</li>
                <li>备份包含该租户的所有业务数据</li>
              </ul>
              <Divider />
              <p><strong>恢复：</strong></p>
              <ul>
                <li>选择目标租户和备份文件</li>
                <li>系统将先进行预检，展示备份内容概要</li>
                <li>确认后可选择"覆盖模式"或"合并模式"导入</li>
                <li><Text type="danger">覆盖模式将清空现有数据，请谨慎操作</Text></li>
              </ul>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 预检结果弹窗 */}
      <Modal
        title="备份文件预检结果"
        open={importVisible}
        onCancel={() => {
          setImportVisible(false);
          setPrecheckResult(null);
          setPrecheckFile(null);
        }}
        footer={
          precheckResult?.valid ? (
            <Space>
              <Button onClick={() => setImportVisible(false)}>取消</Button>
              <Button onClick={() => handleImport(false)}>合并导入</Button>
              <Button danger onClick={() => handleImport(true)}>
                覆盖导入
              </Button>
            </Space>
          ) : (
            <Button onClick={() => setImportVisible(false)}>关闭</Button>
          )
        }
      >
        {precheckResult && (
          <>
            {precheckResult.valid ? (
              <Alert
                message="预检通过"
                description={`租户: ${precheckResult.tenant_name}`}
                type="success"
                showIcon
                style={{ marginBottom: 16 }}
              />
            ) : (
              <Alert
                message="预检失败"
                description={precheckResult.warnings?.join('; ') || '备份文件格式无效'}
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}
            {precheckResult.record_counts && (
              <Card size="small" title="数据概要">
                {Object.entries(precheckResult.record_counts).map(([key, count]) => (
                  <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                    <Text>{key}</Text>
                    <Text strong>{count} 条</Text>
                  </div>
                ))}
              </Card>
            )}
          </>
        )}
        {importing && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Spin tip="正在预检..." />
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default DataBackupPage;
