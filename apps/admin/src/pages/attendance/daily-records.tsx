import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Card, Col, Row, Statistic, Tag, Button, App, DatePicker } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  LogoutOutlined,
  LoginOutlined,
  TeamOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useRef, useState, useCallback } from 'react';
import { attendanceApi } from '@hospital/api';
import type { AttendanceRecord, DailyStat } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useRequest } from '@umijs/max';
import dayjs from 'dayjs';

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

const DailyRecordsPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [selectedDate, setSelectedDate] = useState<string>(dayjs().format('YYYY-MM-DD'));

  const { data: stats, loading: statsLoading, run: fetchStats } = useRequest(
    () => attendanceApi.getDailyStats(selectedDate),
    {
      refreshDeps: [selectedDate],
      onError: () => {
        message.error('获取每日统计失败');
      },
    },
  );

  const handleQuery = useCallback(() => {
    fetchStats();
    actionRef.current?.reload();
  }, [fetchStats]);

  const dailyStat = stats as DailyStat | undefined;

  const columns: ProColumns<AttendanceRecord>[] = [
    {
      title: '账号名',
      dataIndex: 'accountName',
      width: 120,
    },
    {
      title: '班次',
      dataIndex: 'shiftName',
      width: 100,
      search: false,
      render: (_, record) => record.shiftName || '-',
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
        // 严重迟到/早退使用红色高亮
        const isSevere =
          (record.status === 'late' && record.lateMinutes > 30) ||
          (record.status === 'early' && record.earlyMinutes > 30);
        const tagColor = isSevere ? 'red' : s.color;
        const label = isSevere
          ? record.status === 'late'
            ? `严重迟到 ${record.lateMinutes}分`
            : `严重早退 ${record.earlyMinutes}分`
          : s.text;
        return (
          <Tag color={tagColor} icon={isSevere ? <WarningOutlined /> : getStatusIcon(record.status)}>
            {label}
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
          <span style={{ color: 'var(--color-evening)' }}>{record.lateMinutes}</span>
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
  ];

  return (
    <PageContainer title="公司每日记录">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="总人数"
              value={dailyStat?.total ?? 0}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="正常"
              value={dailyStat?.normal ?? 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="迟到"
              value={dailyStat?.late ?? 0}
              valueStyle={{ color: 'var(--color-evening)' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="早退"
              value={dailyStat?.early ?? 0}
              valueStyle={{ color: '#fa541c' }}
              prefix={<LogoutOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="缺勤"
              value={dailyStat?.absent ?? 0}
              valueStyle={{ color: 'var(--color-error-active)' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="请假"
              value={dailyStat?.leave ?? 0}
              valueStyle={{ color: 'var(--color-primary)' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading}>
            <Statistic
              title="待打卡"
              value={dailyStat?.expected ?? 0}
              valueStyle={{ color: 'var(--color-primary)' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card loading={statsLoading} style={{ borderColor: 'var(--color-error)' }}>
            <Statistic
              title="异常"
              value={(dailyStat?.late ?? 0) + (dailyStat?.early ?? 0) + (dailyStat?.absent ?? 0)}
              valueStyle={{ color: 'var(--color-error)' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <ProTable<AttendanceRecord>
        headerTitle="每日考勤明细"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        request={createListRequest(
          (params: any) =>
            attendanceApi.getAllRecords({
              ...params,
              startDate: selectedDate,
              endDate: selectedDate,
            }),
        )}
        toolBarRender={() => [
          <DatePicker
            key="date"
            value={dayjs(selectedDate)}
            onChange={(date) => {
              if (date) {
                setSelectedDate(date.format('YYYY-MM-DD'));
              }
            }}
            allowClear={false}
          />,
          <Button
            key="query"
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleQuery}
          >
            查询
          </Button>,
        ]}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
      />
    </PageContainer>
  );
};

export default DailyRecordsPage;
