import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Space, Modal, Grid, Alert, Statistic, Card, Row, Col } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { history, useAccess } from '@umijs/max';

const { useBreakpoint } = Grid;
import { ruleSetApi, dataApi, shiftTypeApi } from '@hospital/api';
import type { RuleSet } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';
import { RuleSetPreviewDrawer } from '@/components/rule-set-visualization';
import { getRuleSetColumns } from './components/RuleSetTableColumns';
import { confirmDelete } from '@/components/ConfirmModal';

const RuleSetsPage: React.FC = () => {
  const { message: antMessage } = App.useApp();
  const access = useAccess();
  const screens = useBreakpoint();
  const isMobile = !screens.md; // 小于 768px
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<RuleSet[]>([]);
  const [selectedRuleSet, setSelectedRuleSet] = useState<RuleSet | null>(null);
  const [shiftTypes, setShiftTypes] = useState<any[]>([]);

  // 批量操作 Modal 状态
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchType, setBatchType] = useState<'enable' | 'disable' | 'delete' | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);

  // 统计信息
  const [stats, setStats] = useState({ total: 0, enabled: 0, disabled: 0, active: 0 });

  const handleDelete = async (id: string) => {
    try {
      await ruleSetApi.delete(id);
      antMessage.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      antMessage.error(error.message || '删除失败');
    }
  };

  const handleToggleEnabled = async (record: RuleSet) => {
    try {
      if (record.enabled) {
        await ruleSetApi.disable(record.id);
        antMessage.success('已禁用');
      } else {
        await ruleSetApi.enable(record.id);
        antMessage.success('已启用');
      }
      actionRef.current?.reload();
    } catch (error: any) {
      antMessage.error(error.message || '操作失败');
    }
  };

  // ==================== 批量操作 ====================
  const handleBatchEnable = () => {
    const disabledRows = selectedRows.filter(r => !r.enabled);
    if (disabledRows.length === 0) {
      antMessage.warning('请选择已禁用的规则组');
      return;
    }
    setBatchType('enable');
    setBatchError(null);
    setBatchModalOpen(true);
  };

  const executeBatchEnable = async () => {
    const disabledRows = selectedRows.filter(r => !r.enabled);
    setBatchLoading(true);
    setBatchError(null);
    try {
      await Promise.all(disabledRows.map(r => ruleSetApi.enable(r.id)));
      antMessage.success(`批量启用成功 (${disabledRows.length} 条)`);
      setSelectedRowKeys([]);
      setSelectedRows([]);
      actionRef.current?.reload();
      setBatchModalOpen(false);
    } catch (error: any) {
      setBatchError(error.message || '批量启用失败，请重试');
    } finally {
      setBatchLoading(false);
    }
  };

  const handleBatchDisable = () => {
    const enabledRows = selectedRows.filter(r => r.enabled);
    if (enabledRows.length === 0) {
      antMessage.warning('请选择已启用的规则组');
      return;
    }
    setBatchType('disable');
    setBatchError(null);
    setBatchModalOpen(true);
  };

  const executeBatchDisable = async () => {
    const enabledRows = selectedRows.filter(r => r.enabled);
    setBatchLoading(true);
    setBatchError(null);
    try {
      await Promise.all(enabledRows.map(r => ruleSetApi.disable(r.id)));
      antMessage.success(`批量禁用成功 (${enabledRows.length} 条)`);
      setSelectedRowKeys([]);
      setSelectedRows([]);
      actionRef.current?.reload();
      setBatchModalOpen(false);
    } catch (error: any) {
      setBatchError(error.message || '批量禁用失败，请重试');
    } finally {
      setBatchLoading(false);
    }
  };

  const handleBatchDelete = () => {
    if (!access.canSuperAdmin) {
      antMessage.error('只有超级管理员可以删除规则组');
      return;
    }
    setBatchType('delete');
    setBatchError(null);
    setBatchModalOpen(true);
  };

  const executeBatchDelete = async () => {
    setBatchLoading(true);
    setBatchError(null);
    try {
      await Promise.all(selectedRows.map(r => ruleSetApi.delete(r.id)));
      antMessage.success(`批量删除成功 (${selectedRows.length} 条)`);
      setSelectedRowKeys([]);
      setSelectedRows([]);
      actionRef.current?.reload();
      setBatchModalOpen(false);
    } catch (error: any) {
      setBatchError(error.message || '批量删除失败，请重试');
    } finally {
      setBatchLoading(false);
    }
  };

  // 获取批量操作的内容
  const getBatchModalContent = () => {
    const disabledRows = selectedRows.filter(r => !r.enabled);
    const enabledRows = selectedRows.filter(r => r.enabled);

    switch (batchType) {
      case 'enable':
        return (
          <div>
            <p>确定要启用选中的 <strong>{disabledRows.length}</strong> 条规则组吗？</p>
            <p style={{ color: '#1890ff', marginTop: 8 }}>
              启用后，规则组将立即生效，影响对应班次类型的预约流程。
            </p>
            {batchError && (
              <Alert message={batchError} type="error" showIcon style={{ marginTop: 12 }} />
            )}
          </div>
        );
      case 'disable':
        return (
          <div>
            <p>确定要禁用选中的 <strong>{enabledRows.length}</strong> 条规则组吗？</p>
            <p style={{ color: '#1890ff', marginTop: 8 }}>
              禁用后，规则组将不再生效，已创建的预约不受影响。
            </p>
            {batchError && (
              <Alert message={batchError} type="error" showIcon style={{ marginTop: 12 }} />
            )}
          </div>
        );
      case 'delete':
        const affectedShiftTypes = new Set<string>();
        selectedRows.forEach(row => {
          row.shiftTypes?.forEach(st => {
            affectedShiftTypes.add(st.name);
          });
        });
        const shiftTypesList = Array.from(affectedShiftTypes).join('、');
        return (
          <div>
            <p>确定要删除选中的 <strong>{selectedRows.length}</strong> 条规则组吗？</p>
            {shiftTypesList && (
              <p style={{ marginTop: 8 }}>这将影响以下班次类型：{shiftTypesList}</p>
            )}
            {batchError && (
              <Alert message={batchError} type="error" showIcon style={{ marginTop: 12 }} />
            )}
          </div>
        );
      default:
        return null;
    }
  };

  const getBatchModalTitle = () => {
    switch (batchType) {
      case 'enable':
        return '确认批量启用';
      case 'disable':
        return '确认批量禁用';
      case 'delete':
        return '确认批量删除';
      default:
        return '确认操作';
    }
  };

  const handleBatchModalOk = () => {
    switch (batchType) {
      case 'enable':
        executeBatchEnable();
        break;
      case 'disable':
        executeBatchDisable();
        break;
      case 'delete':
        executeBatchDelete();
        break;
    }
  };

  // 使用提取的列定义
  const columns: ProColumns<RuleSet>[] = getRuleSetColumns({
    handleToggleEnabled,
    handleDelete,
    handleView: (record) => setSelectedRuleSet(record),
    canSuperAdmin: access.canSuperAdmin,
  });

  // 添加班次类型筛选列
  columns.unshift({
    title: '班次类型',
    dataIndex: 'shift_type_id',
    hideInTable: true,
    request: async () => {
      if (shiftTypes.length === 0) {
        const data = await shiftTypeApi.getAll();
        setShiftTypes(data);
        return data.map((st: any) => ({ label: st.name, value: st.id }));
      }
      return shiftTypes.map((st: any) => ({ label: st.name, value: st.id }));
    },
  });

  // 加载班次类型
  useEffect(() => {
    shiftTypeApi.getAll().then((data) => {
      setShiftTypes(data);
    }).catch((error) => {
      console.error('加载班次类型失败', error);
    });
  }, []);

  return (
    <PageContainer>
      <Alert
        message="规则组说明"
        description="规则组通过班次类型关联排班，控制预约时间窗、预约限制、签到规则和容量管理等业务规则。每个班次类型仅使用优先级最高的启用规则组。"
        type="info"
        showIcon
        closable
        style={{ marginBottom: 16 }}
      />
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small"><Statistic title="规则组总数" value={stats.total} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="启用" value={stats.enabled} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="禁用" value={stats.disabled} valueStyle={{ color: '#8c8c8c' }} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="生效中" value={stats.active} valueStyle={{ color: '#1890ff' }} /></Card>
        </Col>
      </Row>
      <ProTable<RuleSet>
        headerTitle="规则组列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys, rows) => {
            setSelectedRowKeys(keys as string[]);
            setSelectedRows(rows);
          },
        }}
        search={{
          labelWidth: 'auto',
        }}
        request={async (params) => {
          const result = await ruleSetApi.getList({
            enabled: params.enabled === 'true' ? true : params.enabled === 'false' ? false : undefined,
            shiftTypeId: params.shift_type_id,
            page: params.current,
            pageSize: params.pageSize,
          });
          // 更新统计信息
          const items = result.data || [];
          setStats({
            total: result.total || 0,
            enabled: items.filter(r => r.enabled).length,
            disabled: items.filter(r => !r.enabled).length,
            active: items.filter(r => r.isActive).length,
          });
          return {
            data: result.data || [],
            success: true,
            total: result.total || 0,
          };
        }}
        toolBarRender={() => [
          <ImportExport
            key="import-export"
            moduleName="规则组"
            exportUrl={dataApi.getExportRuleSetsUrl()}
            importUrl={dataApi.getImportRuleSetsUrl()}
            templateUrl={dataApi.getRuleSetTemplateUrl()}
            onImportSuccess={() => actionRef.current?.reload()}
          />,
          selectedRowKeys.length > 0 && (
            <Space key="batch-actions" wrap={isMobile}>
              <Button size={isMobile ? 'middle' : 'small'} onClick={handleBatchEnable}>
                批量启用
              </Button>
              <Button size={isMobile ? 'middle' : 'small'} onClick={handleBatchDisable}>
                批量禁用
              </Button>
              {access.canSuperAdmin && (
                <Button danger size={isMobile ? 'middle' : 'small'} onClick={handleBatchDelete}>
                  批量删除
                </Button>
              )}
            </Space>
          ),
          access.canSuperAdmin && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/operations/system/rule-sets/create')}
            >
              {isMobile ? '新增' : '新增规则组'}
            </Button>
          ),
        ]}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
      />

      {/* 规则组预览抽屉 */}
      <RuleSetPreviewDrawer
        open={!!selectedRuleSet}
        onClose={() => setSelectedRuleSet(null)}
        ruleSet={selectedRuleSet}
        width={isMobile ? window.innerWidth * 0.95 : 600}
      />

      {/* 批量操作确认弹窗 */}
      <Modal
        title={getBatchModalTitle()}
        open={batchModalOpen}
        onOk={handleBatchModalOk}
        onCancel={() => {
          if (!batchLoading) {
            setBatchModalOpen(false);
            setBatchError(null);
          }
        }}
        confirmLoading={batchLoading}
        okButtonProps={{ disabled: !!batchError }}
        cancelText="取消"
        okText="确认"
      >
        {getBatchModalContent()}
      </Modal>
    </PageContainer>
  );
};

export default RuleSetsPage;
