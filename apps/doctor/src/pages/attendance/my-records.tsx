import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag, App } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  LogoutOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  LoginOutlined,
} from '@ant-design/icons';
import { attendanceApi } from '@hospital/api';
import type { AttendanceRecord } from '@hospital/api';
import dayjs from 'dayjs';

const STATUS_MAP: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  normal: { text: '正常', color: 'green', icon: <CheckCircleOutlined /> },
  late: { text: '迟到', color: 'orange', icon: <ClockCircleOutlined /> },
  early: { text: '早退', color: 'volcano', icon: <LogoutOutlined /> },
  absent: { text: '缺勤', color: 'red', icon: <CloseCircleOutlined /> },
  leave: { text: '请假', color: 'blue', icon: <ExclamationCircleOutlined /> },
  field_work: { text: '外勤', color: 'purple', icon: <LoginOutlined /> },
};

const formatWorkHours = (hours?: number | null): string => {
  if (hours === undefined || hours === null) return '-';
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h === 0) return `${m}分钟`;
  if (m === 0) return `${h}小时`;
  return `${h}小时${m}分钟`;
};

const MyAttendanceRecords: React.FC = () => {
  const { message } = App.useApp();

  const columns: ProColumns<AttendanceRecord>[] = [
    {
      title: '日期',
      dataIndex: 'checkDate',
      width: 120,
      sorter: true,
      render: (_, record) => record.checkDate || '-',
    },
    {
      title: '班次',
      dataIndex: 'shiftName',
      width: 100,
      ellipsis: true,
      render: (_, record) => record.shiftName || '-',
    },
    {
      title: '签到时间',
      dataIndex: 'checkInTime',
      width: 170,
      render: (_, record) =>
        record.checkInTime ? dayjs(record.checkInTime).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '签退时间',
      dataIndex: 'checkOutTime',
      width: 170,
      render: (_, record) =>
        record.checkOutTime ? dayjs(record.checkOutTime).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (_, record) => {
        const s = STATUS_MAP[record.status] || { text: record.status, color: 'default', icon: null };
        return (
          <Tag color={s.color} icon={s.icon}>
            {s.text}
          </Tag>
        );
      },
      valueEnum: {
        normal: { text: '正常', status: 'Success' },
        late: { text: '迟到', status: 'Warning' },
        early: { text: '早退', status: 'Error' },
        absent: { text: '缺勤', status: 'Error' },
        leave: { text: '请假', status: 'Processing' },
        field_work: { text: '外勤', status: 'Default' },
      },
    },
    {
      title: '迟到',
      dataIndex: 'lateMinutes',
      width: 80,
      render: (_, record) =>
        record.lateMinutes > 0 ? <Tag color="orange">{record.lateMinutes}分钟</Tag> : '-',
      search: false,
    },
    {
      title: '早退',
      dataIndex: 'earlyMinutes',
      width: 80,
      render: (_, record) =>
        record.earlyMinutes > 0 ? <Tag color="volcano">{record.earlyMinutes}分钟</Tag> : '-',
      search: false,
    },
    {
      title: '工作时长',
      dataIndex: 'workHours',
      width: 100,
      render: (_, record) => formatWorkHours(record.workHours),
      search: false,
    },
    {
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
      search: false,
    },
  ];

  return (
    <PageContainer title="我的考勤记录">
      <ProTable<AttendanceRecord>
        rowKey="id"
        columns={columns}
        request={async (params) => {
          try {
            const { current, pageSize, checkDateRange, status, ...rest } = params;
            const res = await attendanceApi.getMyRecords({
              startDate: checkDateRange?.[0],
              endDate: checkDateRange?.[1],
              page: current,
              pageSize,
              ...rest,
            });
            return {
              data: res.data || [],
              total: res.total || 0,
              success: true,
            };
          } catch (error: any) {
            message.error(error.message || '获取考勤记录失败');
            return { data: [], total: 0, success: false };
          }
        }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
          optionRender: (searchConfig, formProps, dom) => dom,
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
        dateFormatter="string"
        toolBarRender={false}
      />
    </PageContainer>
  );
};

export default MyAttendanceRecords;
