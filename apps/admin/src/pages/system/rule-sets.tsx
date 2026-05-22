import { PlusOutlined, CalendarOutlined, DashboardOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Space, Modal, Grid, Alert, Tag, Drawer, Descriptions, Table, Select, Statistic, Row, Col, Card, Spin, Popconfirm } from 'antd';
import { useRef, useState, useCallback, useEffect } from 'react';
import { history, useAccess } from '@umijs/max';

const { useBreakpoint } = Grid;
import { ruleSetApi, dataApi } from '@hospital/api';
import type { RuleSet } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';
import { RuleSetPreviewDrawer } from '@/components/rule-set-visualization';
import { getRuleSetColumns } from './components/RuleSetTableColumns';

interface PerfLatency {
  p50?: number;
  p95?: number;
  p99?: number;
  avg?: number;
  max?: number;
  min?: number;
}

interface PerfOperationStats {
  count: number;
  avgMs: number;
  p95Ms?: number;
  slowCount?: number;
}

interface PerfStats {
  totalCalls: number;
  slowQueryCount: number;
  callsPerMinute: number;
  latency?: PerfLatency;
  byOperation?: Record<string, PerfOperationStats>;
}

interface SlowQuery {
  id: string;
  operation: string;
  durationMs: number;
  query: string;
  timestamp: string;
}

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

  // 性能监控状态
  const [perfDrawerOpen, setPerfDrawerOpen] = useState(false);
  const [perfLoading, setPerfLoading] = useState(false);
  const [perfStats, setPerfStats] = useState<PerfStats | null>(null);
  const [slowQueries, setSlowQueries] = useState<SlowQuery[]>([]);
  const [perfHours, setPerfHours] = useState(24);

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

  // 性能监控
  const loadPerfData = useCallback(async () => {
    setPerfLoading(true);
    try {
      const [statsResult, slowResult] = await Promise.all([
        ruleSetApi.getPerformanceStats({ hours: perfHours }),
        ruleSetApi.getSlowQueries({ limit: 50 }),
      ]);
      setPerfStats(statsResult);
      setSlowQueries(slowResult?.data || []);
    } catch {
      antMessage.error('加载性能数据失败');
    } finally {
      setPerfLoading(false);
    }
  }, [perfHours]);

  useEffect(() => {
    if (perfDrawerOpen) loadPerfData();
  }, [perfDrawerOpen, loadPerfData]);

  const handleClearMetrics = async () => {
    try {
      await ruleSetApi.clearPerformanceMetrics();
      antMessage.success('性能指标已清除');
      loadPerfData();
    } catch (error: any) {
      antMessage.error(error.message || '清除失败');
    }
  };

  // 使用提取的列定义
  const columns: ProColumns<RuleSet>[] = getRuleSetColumns({
    handleToggleEnabled,
    handleDelete,
    handleView: (record) => setSelectedRuleSet(record),
    handleAudit: (record) => {
      history.push(`/organization/medical-config/rule-sets/${record.id}/audit?name=${encodeURIComponent(record.name || '')}`);
    },
    canSuperAdmin: access.canSuperAdmin,
  });

  return (
    <PageContainer>
      <Alert
        title="规则组说明"
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
          <Button
            key="schedule-rules"
            icon={<CalendarOutlined />}
            onClick={() => history.push('/medical-services/schedule/rule')}
          >
            排班模板
          </Button>,
          access.canSuperAdmin && (
            <Button
              key="performance"
              icon={<DashboardOutlined />}
              onClick={() => setPerfDrawerOpen(true)}
            >
              性能监控
            </Button>
          ),
          <ImportExport
            key="import-export"
            moduleName="规则组"
            exportUrl={dataApi.getExportRuleSetsUrl()}
            importUrl={dataApi.getImportRuleSetsUrl()}
            templateUrl={dataApi.getRuleSetTemplateUrl()}
            onImportSuccess={() => actionRef.current?.reload()}
          />,
          selectedRowKeys.length > 0 && access.canSuperAdmin && (
            <Space key="batch-actions" wrap={isMobile}>
              <Button size={isMobile ? 'middle' : 'small'} onClick={handleBatchEnable}>
                批量启用
              </Button>
              <Button size={isMobile ? 'middle' : 'small'} onClick={handleBatchDisable}>
                批量禁用
              </Button>
              <Button danger size={isMobile ? 'middle' : 'small'} onClick={handleBatchDelete}>
                批量删除
              </Button>
            </Space>
          ),
          access.canSuperAdmin && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/organization/medical-config/rule-sets/create')}
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

      {/* 性能监控抽屉 */}
      <Drawer
        title="规则引擎性能监控"
        open={perfDrawerOpen}
        onClose={() => setPerfDrawerOpen(false)}
        width={isMobile ? window.innerWidth * 0.95 : 700}
        extra={
          <Space>
            <Select
              value={perfHours}
              onChange={setPerfHours}
              options={[
                { label: '最近 1 小时', value: 1 },
                { label: '最近 6 小时', value: 6 },
                { label: '最近 24 小时', value: 24 },
                { label: '最近 3 天', value: 72 },
                { label: '最近 7 天', value: 168 },
              ]}
              style={{ width: 130 }}
            />
            <Popconfirm title="确定清除所有性能指标？" onConfirm={handleClearMetrics}>
              <Button danger size="small">清除指标</Button>
            </Popconfirm>
          </Space>
        }
      >
        <Spin spinning={perfLoading}>
          {perfStats && (
            <>
              <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col span={8}>
                  <Statistic title="总调用次数" value={perfStats.totalCalls || 0} />
                </Col>
                <Col span={8}>
                  <Statistic title="慢查询数" value={perfStats.slowQueryCount || 0} valueStyle={{ color: '#cf1322' }} />
                </Col>
                <Col span={8}>
                  <Statistic title="调用速率" value={perfStats.callsPerMinute || 0} precision={2} suffix="次/分" />
                </Col>
              </Row>

              {perfStats.latency && (
                <Card title="延迟统计" size="small" style={{ marginBottom: 16 }}>
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="P50">{perfStats.latency.p50?.toFixed(2)} ms</Descriptions.Item>
                    <Descriptions.Item label="P95">{perfStats.latency.p95?.toFixed(2)} ms</Descriptions.Item>
                    <Descriptions.Item label="P99">{perfStats.latency.p99?.toFixed(2)} ms</Descriptions.Item>
                    <Descriptions.Item label="平均值">{perfStats.latency.avg?.toFixed(2)} ms</Descriptions.Item>
                    <Descriptions.Item label="最大值">{perfStats.latency.max?.toFixed(2)} ms</Descriptions.Item>
                    <Descriptions.Item label="最小值">{perfStats.latency.min?.toFixed(2)} ms</Descriptions.Item>
                  </Descriptions>
                </Card>
              )}

              {perfStats.byOperation && Object.keys(perfStats.byOperation).length > 0 && (
                <Card title="按操作类型" size="small" style={{ marginBottom: 16 }}>
                  <Table
                    dataSource={Object.entries(perfStats.byOperation).map(([op, data]: [string, PerfOperationStats]) => ({
                      operation: op,
                      ...data,
                    }))}
                    rowKey="operation"
                    size="small"
                    pagination={false}
                    columns={[
                      { title: '操作', dataIndex: 'operation', width: 120 },
                      { title: '调用次数', dataIndex: 'count', width: 80 },
                      { title: '平均延迟(ms)', dataIndex: 'avgLatency', width: 110, render: (v: number) => v?.toFixed(2) },
                      { title: 'P95(ms)', dataIndex: 'p95', width: 90, render: (v: number) => v?.toFixed(2) },
                      { title: '慢查询', dataIndex: 'slowCount', width: 80 },
                    ]}
                  />
                </Card>
              )}
            </>
          )}

          <Card title="慢查询列表" size="small">
            <Table
              dataSource={slowQueries}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 20 }}
              columns={[
                { title: '时间', dataIndex: 'timestamp', width: 170, render: (v: string) => v?.slice(0, 19)?.replace('T', ' ') || '-' },
                { title: '操作', dataIndex: 'operation', width: 120, ellipsis: true },
                { title: '耗时(ms)', dataIndex: 'duration', width: 90, render: (v: number) => v?.toFixed(2) },
                { title: '详情', dataIndex: 'details', ellipsis: true },
              ]}
            />
          </Card>
        </Spin>
      </Drawer>

    </PageContainer>
  );
};

export default RuleSetsPage;
