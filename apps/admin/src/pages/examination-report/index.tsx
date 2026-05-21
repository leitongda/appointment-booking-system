import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Space, Tag, Popconfirm, Descriptions, Drawer, Spin, Button } from 'antd';
import { EyeOutlined, DeleteOutlined, DownloadOutlined, FileOutlined } from '@ant-design/icons';
import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { examinationReportApi, storeApi, doctorApi } from '@hospital/api';
import type { ExaminationReportListItem } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import ListPageSkeleton from '@/components/ListPageSkeleton';
import dayjs from 'dayjs';

const REPORT_TYPE_MAP: Record<string, { text: string; color: string }> = {
  blood_test: { text: '血液检验', color: 'red' },
  imaging: { text: '影像检查', color: 'blue' },
  pathology: { text: '病理报告', color: 'purple' },
  other: { text: '其他', color: 'default' },
};

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const ExaminationReportPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [initialLoading, setInitialLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentReport, setCurrentReport] = useState<any>(null);

  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  const handleView = useCallback(async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await examinationReportApi.getDetail(id);
      setCurrentReport(result);
    } catch (error: any) {
      message.error(error.message || '加载报告详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }, [message]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await examinationReportApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  }, [message]);

  useEffect(() => { setInitialLoading(false); }, []);

  // 日期快捷选项
  const datePresets: { label: string; value: [dayjs.Dayjs, dayjs.Dayjs] }[] = [
    { label: '今天', value: [dayjs(), dayjs()] },
    { label: '本周', value: [dayjs().startOf('week'), dayjs().endOf('week')] },
    { label: '本月', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
    { label: '近7天', value: [dayjs().subtract(6, 'day'), dayjs()] },
    { label: '近30天', value: [dayjs().subtract(29, 'day'), dayjs()] },
  ];

  const columns = useMemo<ProColumns<ExaminationReportListItem>[]>(() => [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '报告标题/文件名',
      },
    },
    // 超级管理员和多门店管理员可以按门店筛选
    ...(showStoreFilter
      ? [
          {
            title: '门店',
            dataIndex: 'storeId',
            hideInTable: true,
            valueType: 'select',
            request: async () => {
              try {
                const stores = await storeApi.getAll();
                let storeList = stores ?? [];
                if (!isSuperAdmin && currentUser?.storeIds?.length) {
                  storeList = storeList.filter((s: any) =>
                    currentUser.storeIds?.includes(s.id)
                  );
                }
                return [
                  { label: '全部门店', value: '' },
                  ...storeList.map((s: any) => ({
                    label: s.name,
                    value: s.id,
                  })),
                ];
              } catch {
                return [];
              }
            },
          } as ProColumns<ExaminationReportListItem>,
        ]
      : []),
    {
      title: '报告类型',
      dataIndex: 'reportType',
      hideInTable: true,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(REPORT_TYPE_MAP).map(([key, value]) => [
          key,
          { text: value.text },
        ])
      ),
    },
    {
      title: '医生',
      dataIndex: 'doctorId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择医生',
      },
      request: async () => {
        try {
          const doctors = await fetchAllData((page, pageSize) =>
            doctorApi.getList({ page, pageSize })
          );
          return [
            { label: '全部医生', value: '' },
            ...doctors.map((d: any) => ({
              label: `${d.name}（${d.departmentName || '无科室'}）`,
              value: d.id,
            })),
          ];
        } catch {
          return [];
        }
      },
    },
    {
      title: '上传日期',
      dataIndex: 'dateRange',
      hideInTable: true,
      valueType: 'dateRange',
      fieldProps: {
        presets: datePresets,
      },
      search: {
        transform: (value) => {
          if (!value) return {};
          return {
            startDate: value[0],
            endDate: value[1],
          };
        },
      },
    },
    // 表格展示列
    {
      title: '报告标题',
      dataIndex: 'title',
      ellipsis: true,
      search: false,
    },
    {
      title: '报告类型',
      dataIndex: 'reportType',
      width: 100,
      search: false,
      render: (_, record) => {
        const typeInfo = REPORT_TYPE_MAP[record.reportType] || {
          text: '未知',
          color: 'default',
        };
        return <Tag color={typeInfo.color}>{typeInfo.text}</Tag>;
      },
    },
    {
      title: '文件名',
      dataIndex: 'fileName',
      ellipsis: true,
      search: false,
      render: (val) => (
        <Space>
          <FileOutlined />
          {val || '-'}
        </Space>
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'fileSize',
      width: 100,
      search: false,
      render: (val) => (val != null ? formatFileSize(Number(val)) : '-'),
    },
    {
      title: '上传时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <a onClick={() => handleView(record.id)} style={{ fontSize: 13 }}>
            <EyeOutlined /> 详情
          </a>
          {record.fileUrl && (
            <a
              href={record.fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13 }}
            >
              <DownloadOutlined /> 下载
            </a>
          )}
          <Popconfirm
            title="确定删除该报告吗？此操作不可恢复。"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f', fontSize: 13 }}>
              <DeleteOutlined /> 删除
            </a>
          </Popconfirm>
        </Space>
      ),
    },
  ], [showStoreFilter, isSuperAdmin, currentUser, handleView, handleDelete]);

  return (
    <PageContainer>
      {initialLoading && <ListPageSkeleton filterCount={5} rowCount={6} />}
      {!initialLoading && (
        <ProTable<ExaminationReportListItem>
          headerTitle="检查报告"
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={async (params) => {
            const {
              current,
              pageSize,
              keyword,
              storeId,
              reportType,
              doctorId,
              startDate,
              endDate,
            } = params;
            return toProTableResult(
              await examinationReportApi.adminList({
                keyword: keyword || undefined,
                storeId: storeId || undefined,
                reportType: reportType || undefined,
                doctorId: doctorId || undefined,
                startDate: startDate || undefined,
                endDate: endDate || undefined,
                page: current,
                pageSize,
              })
            );
          }}
          pagination={{
            defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE,
          }}
          search={{ labelWidth: 'auto' }}
        />
      )}

      <Drawer
        title="报告详情"
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentReport(null);
        }}
        width={720}
      >
        <Spin spinning={detailLoading}>
          {currentReport ? (
            <Descriptions column={2} bordered size="small" items={[
              { key: 'id', label: '报告ID', children: currentReport.id },
              { key: 'title', label: '标题', children: currentReport.title },
              { key: 'reportType', label: '报告类型', children: (
                <Tag color={REPORT_TYPE_MAP[currentReport.reportType]?.color || 'default'}>
                  {REPORT_TYPE_MAP[currentReport.reportType]?.text || '未知'}
                </Tag>
              ) },
              { key: 'description', label: '描述', span: 2, children: currentReport.description || '-' },
              { key: 'fileName', label: '文件名', children: currentReport.fileName || '-' },
              { key: 'fileSize', label: '文件大小', children: currentReport.fileSize != null ? formatFileSize(currentReport.fileSize) : '-' },
              { key: 'fileType', label: '文件类型', children: currentReport.fileType || '-' },
              { key: 'fileUrl', label: '文件链接', children: currentReport.fileUrl ? (
                <a href={currentReport.fileUrl} target="_blank" rel="noopener noreferrer">
                  <DownloadOutlined /> 下载/查看
                </a>
              ) : '-' },
              { key: 'appointmentId', label: '预约ID', children: currentReport.appointmentId || '-' },
              { key: 'patientId', label: '患者ID', children: currentReport.patientId || '-' },
              { key: 'doctorId', label: '医生ID', children: currentReport.doctorId || '-' },
              { key: 'recordId', label: '病历ID', children: currentReport.recordId || '-' },
              { key: 'createdAt', label: '创建时间', children: currentReport.createdAt ? dayjs(currentReport.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
              { key: 'updatedAt', label: '更新时间', children: currentReport.updatedAt ? dayjs(currentReport.updatedAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
            ]} />
          ) : null}
        </Spin>
      </Drawer>
    </PageContainer>
  );
};

export default ExaminationReportPage;
