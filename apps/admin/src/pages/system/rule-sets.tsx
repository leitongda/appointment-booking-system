import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Space, Modal, message } from 'antd';
import { useRef, useState } from 'react';
import { history, useAccess } from '@umijs/max';
import { ruleSetApi, dataApi } from '@hospital/api';
import type { RuleSet } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';
import { RuleSetPreviewDrawer } from '@/components/rule-set-visualization';
import { getRuleSetColumns } from './components/RuleSetTableColumns';

const RuleSetsPage: React.FC = () => {
  const { message: antMessage } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<RuleSet[]>([]);
  const [selectedRuleSet, setSelectedRuleSet] = useState<RuleSet | null>(null);

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

    Modal.confirm({
      title: '确认批量启用',
      content: `确定要启用选中的 ${disabledRows.length} 条规则组吗？`,
      onOk: async () => {
        try {
          await Promise.all(disabledRows.map(r => ruleSetApi.enable(r.id)));
          antMessage.success('批量启用成功');
          setSelectedRowKeys([]);
          setSelectedRows([]);
          actionRef.current?.reload();
        } catch (error: any) {
          antMessage.error(error.message || '批量启用失败');
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
      content: `确定要禁用选中的 ${enabledRows.length} 条规则组吗？`,
      onOk: async () => {
        try {
          await Promise.all(enabledRows.map(r => ruleSetApi.disable(r.id)));
          antMessage.success('批量禁用成功');
          setSelectedRowKeys([]);
          setSelectedRows([]);
          actionRef.current?.reload();
        } catch (error: any) {
          antMessage.error(error.message || '批量禁用失败');
        }
      },
    });
  };

  const handleBatchDelete = () => {
    if (!access.canSuperAdmin) {
      antMessage.error('只有超级管理员可以删除规则组');
      return;
    }

    Modal.confirm({
      title: '确认批量删除',
      content: (
        <div>
          <p>确定要删除选中的 <strong>{selectedRows.length}</strong> 条规则组吗？</p>
          <p style={{ color: '#ff4d4f' }}>⚠️ 删除后相关配置也会受影响，此操作不可恢复！</p>
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      onOk: async () => {
        try {
          await Promise.all(selectedRows.map(r => ruleSetApi.delete(r.id)));
          antMessage.success('批量删除成功');
          setSelectedRowKeys([]);
          setSelectedRows([]);
          actionRef.current?.reload();
        } catch (error: any) {
          antMessage.error(error.message || '批量删除失败');
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
            page: params.current,
            pageSize: params.pageSize,
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
            <Space key="batch-actions">
              <Button size="small" onClick={handleBatchEnable}>
                批量启用
              </Button>
              <Button size="small" onClick={handleBatchDisable}>
                批量禁用
              </Button>
              {access.canSuperAdmin && (
                <Button danger size="small" onClick={handleBatchDelete}>
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
              onClick={() => history.push('/system/rule-sets/create')}
            >
              新增规则组
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
      />
    </PageContainer>
  );
};

export default RuleSetsPage;
