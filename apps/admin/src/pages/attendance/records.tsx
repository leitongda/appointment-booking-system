import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, Tag, App } from 'antd';
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  LoginOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useRef, useState } from 'react';
import axios from 'axios';
import { attendanceApi } from '@hospital/api';
import { getBaseURL } from '@hospital/api';
import { getToken } from '@hospital/shared';
import type { AttendanceRecord } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { downloadBlob } from '@/utils/download';

/** 考勤状态颜色映射 */
const STATUS_MAP: Record<string, { text: string; color: string }> = {
  normal: { text: '正常', color: 'green' },
  late: { text: '迟到', color: 'orange' },
  early: { text: '早退', color: 'volcano' },
  absent: { text: '缺勤', color: 'red' },
  leave: { text: '请假', color: 'blue' },
  field_work: { text: '外勤', color: 'purple' },
  expected: { text: '待打卡', color: 'processing' },
};

/** 获取状态图标 */
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'normal':
      return <CheckCircleOutlined />;
    case 'late':
      return <ClockCircleOutlined />;
    case 'early':
      return <LogoutOutlined />;
    case 'absent':
      return <CloseCircleOutlined />;
    case 'leave':
      return <ExclamationCircleOutlined />;
    case 'field_work':
      return <LoginOutlined />;
    case 'expected':
      return <ClockCircleOutlined />;
    default:
      return undefined;
  }
};

/** 格式化工作时长 */
const formatWorkHours = (hours: number | undefined | null): string => {
  if (hours === undefined || hours === null) return '-';
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h === 0 && m === 0) return '0分';
  if (h === 0) return `${m}分`;
  if (m === 0) return `${h}小时`;
  return `${h}小时${m}分`;
};

const AttendanceRecordsPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [exporting, setExporting] = useState(false);

  /** 导出考勤报表 */
  const handleExport = async () => {
    // 从 ProTable 的搜索表单获取当前筛选条件
    const searchForm = (actionRef.current as any)?.pageInfo;
    const params: Record<string, any> = (actionRef.current as any)?.params || {};

    const startDate = params.startDate;
    const endDate = params.endDate;

    if (!startDate || !endDate) {
      message.warning('请先选择日期范围再导出');
      return;
    }

    setExporting(true);
    try {
      const token = getToken();
      const baseURL = getBaseURL();
      const url = `${baseURL}/attendance/records/export`;
      const response = await axios.get(url, {
        params: {
          start_date: startDate,
          end_date: endDate,
          keyword: params.keyword || undefined,
        },
        responseType: 'blob',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      const blob = response.data as Blob;
      const contentDisposition = response.headers?.['content-disposition'];
      let filename = `考勤报表_${startDate.replace(/-/g, '')}_${endDate.replace(/-/g, '')}.xlsx`;

      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) {
          filename = match[1];
        }
      }

      downloadBlob(blob, filename);
      message.success('导出成功');
    } catch (error: any) {
      message.error(error?.message || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  const columns: ProColumns<AttendanceRecord>[] = [
    {
      title: '账号名',
      dataIndex: 'accountName',
      width: 120,
      search: false,
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '账号名/姓名',
      },
      search: {
        transform: (value: string) => ({ keyword: value }),
      },
    },
    {
      title: '日期范围',
      dataIndex: 'dateRange',
      valueType: 'dateRange',
      width: 240,
      hideInTable: true,
      search: {
        transform: (value: any) => {
          if (Array.isArray(value) && value.length === 2) {
            return { startDate: value[0], endDate: value[1] };
          }
          return {};
        },
      },
    },
    {
      title: '班次',
      dataIndex: 'shiftName',
      width: 100,
      search: false,
      render: (_, record) => record.shiftName || '-',
    },
    {
      title: '打卡日期',
      dataIndex: 'checkDate',
      width: 110,
      search: false,
    },
    {
      title: '上班打卡',
      dataIndex: 'checkInTime',
      width: 90,
      search: false,
      render: (_, record) => {
        if (!record.checkInTime) return '-';
        try {
          const d = new Date(record.checkInTime);
          return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        } catch {
          return record.checkInTime;
        }
      },
    },
    {
      title: '下班打卡',
      dataIndex: 'checkOutTime',
      width: 90,
      search: false,
      render: (_, record) => {
        if (!record.checkOutTime) return '-';
        try {
          const d = new Date(record.checkOutTime);
          return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        } catch {
          return record.checkOutTime;
        }
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueType: 'select',
      valueEnum: {
        normal: { text: '正常' },
        late: { text: '迟到' },
        early: { text: '早退' },
        absent: { text: '缺勤' },
        leave: { text: '请假' },
        field_work: { text: '外勤' },
        expected: { text: '待打卡' },
      },
      render: (_, record) => {
        const s = STATUS_MAP[record.status] || { text: record.status, color: 'default' };
        return (
          <Tag color={s.color} icon={getStatusIcon(record.status)}>
            {s.text}
          </Tag>
        );
      },
    },
    {
      title: '迟到(分)',
      dataIndex: 'lateMinutes',
      width: 90,
      search: false,
      render: (_, record) =>
        record.lateMinutes > 0 ? (
          <span style={{ color: '#fa8c16' }}>{record.lateMinutes}</span>
        ) : (
          '-'
        ),
    },
    {
      title: '早退(分)',
      dataIndex: 'earlyMinutes',
      width: 90,
      search: false,
      render: (_, record) =>
        record.earlyMinutes > 0 ? (
          <span style={{ color: '#fa541c' }}>{record.earlyMinutes}</span>
        ) : (
          '-'
        ),
    },
    {
      title: '工作时长',
      dataIndex: 'workHours',
      width: 100,
      search: false,
      render: (_, record) => formatWorkHours(record.workHours),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      width: 150,
      search: false,
      ellipsis: true,
      render: (_, record) => record.remark || '-',
    },
  ];

  return (
    <PageContainer title="考勤记录">
      <ProTable<AttendanceRecord>
        headerTitle="考勤记录"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        request={createListRequest(attendanceApi.getAllRecords)}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
        columnsState={{
          defaultValue: {
            remark: { show: false },
          } as any,
        }}
        toolBarRender={() => [
          <Button
            key="export"
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={handleExport}
          >
            导出
          </Button>,
        ]}
      />
    </PageContainer>
  );
};

export default AttendanceRecordsPage;
