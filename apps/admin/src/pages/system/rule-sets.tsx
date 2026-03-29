import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Space, Modal, Grid, Alert, Tag } from 'antd';
import { useRef, useState } from 'react';
import { history, useAccess } from '@umijs/max';

const { useBreakpoint } = Grid;
import { ruleSetApi, dataApi } from '@hospital/api';
import type { RuleSet } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';
import { RuleSetPreviewDrawer } from '@/components/rule-set-visualization';
import { getRuleSetColumns } from './components/RuleSetTableColumns';

const RuleSetsPage: React.FC = () => {
  const { message: antMessage } = App.useApp();
  const access = useAccess();
  const screens = useBreakpoint();
  const isMobile = !screens.md; // 小于 768px
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<RuleSet[]>([]);
  const [selectedRuleSet, setSelectedRuleSet] = useState<RuleSet | null>(null);

  // 统计信息
  const [stats, setStats] = useState({ total: 0, enabled: 0, disabled: 0 });

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
  /** 批量操作成功后统一清理 */
  const clearSelection = () => {
    setSelectedRowKeys([]);
    setSelectedRows([]);
    actionRef.current?.reload();
  };

  const handleBatchEnable = () => {
    const disabledRows = selectedRows.filter(r => !r.enabled);
    if (disabledRows.length === 0) {
      antMessage.warning('请选择已禁用的规则组');
      return;
    }
    Modal.confirm({
      title: '确认批量启用',
      content: (
        <div>
          <p>确定要启用选中的 <strong>{disabledRows.length}</strong> 条规则组吗？</p>
          <p style={{ color: '#1890ff', marginTop: 8 }}>
            启用后，规则组将立即生效，影响对应班次类型的预约流程。
          </p>
        </div>
      ),
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await Promise.all(disabledRows.map(r => ruleSetApi.enable(r.id)));
          antMessage.success(`批量启用成功 (${disabledRows.length} 条)`);
          clearSelection();
        } catch (error: any) {
          antMessage.error(error.message || '批量启用失败，请重试');
          throw error;
        }
      },
    });
  };

  const handleBatchDisable = () => {
    const enabledRows = selectedRows.filter(r => r.enabled);
    if (enabledRows.length === 0) {
      antMessage.warning('请选择已启用的规则组');
      return;
    }
    Modal.confirm({
      title: '确认批量禁用',
      content: (
        <div>
          <p>确定要禁用选中的 <strong>{enabledRows.length}</strong> 条规则组吗？</p>
          <p style={{ color: '#1890ff', marginTop: 8 }}>
            禁用后，规则组将不再生效，已创建的预约不受影响。
          </p>
        </div>
      ),
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await Promise.all(enabledRows.map(r => ruleSetApi.disable(r.id)));
          antMessage.success(`批量禁用成功 (${enabledRows.length} 条)`);
          clearSelection();
        } catch (error: any) {
          antMessage.error(error.message || '批量禁用失败，请重试');
          throw error;
        }
      },
    });
  };

  const handleBatchDelete = () => {
    if (!access.canSuperAdmin) {
      antMessage.error('只有超级管理员可以删除规则组');
      return;
    }
    const affectedShiftTypes = new Set<string>();
    selectedRows.forEach(row => {
      row.shiftTypes?.forEach(st => {
        affectedShiftTypes.add(st.name);
      });
    });
    const shiftTypesList = Array.from(affectedShiftTypes).join('、');
    Modal.confirm({
      title: '确认批量删除',
      content: (
        <div>
          <p>确定要删除选中的 <strong>{selectedRows.length}</strong> 条规则组吗？</p>
          {shiftTypesList && (
            <p style={{ marginTop: 8 }}>这将影响以下班次类型：{shiftTypesList}。</p>
          )}
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await Promise.all(selectedRows.map(r => ruleSetApi.delete(r.id)));
          antMessage.success(`批量删除成功 (${selectedRows.length} 条)`);
          clearSelection();
        } catch (error: any) {
          antMessage.error(error.message || '批量删除失败，请重试');
          throw error;
        }
      },
    });
  };

  // 使用提取的列定义
  const columns: ProColumns<RuleSet>[] = getRuleSetColumns({
    handleToggleEnabled,
    handleDelete,
    handleView: (record) => setSelectedRuleSet(record),
    canSuperAdmin: access.canSuperAdmin,
  });

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
      <Space size={16} style={{ marginBottom: 16 }}>
        <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>总数: {stats.total}</Tag>
        <Tag color="success" style={{ fontSize: 14, padding: '4px 12px' }}>已启用: {stats.enabled}</Tag>
        <Tag color="default" style={{ fontSize: 14, padding: '4px 12px' }}>已禁用: {stats.disabled}</Tag>
      </Space>
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
          const data = result.data || [];
          setStats({
            total: result.total || 0,
            enabled: data.filter((r: RuleSet) => r.enabled).length,
            disabled: data.filter((r: RuleSet) => !r.enabled).length,
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

    </PageContainer>
  );
};

export default RuleSetsPage;
