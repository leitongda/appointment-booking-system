/**
 * 会话回放 - 列表页
 *
 * 对应后端：GET /api/v1/session-events（按 session_id 聚合）
 * 行操作「回放」跳详情页 /session-replay/:sessionId
 */
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, Tooltip, Typography } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { history } from '@umijs/max';
import dayjs from 'dayjs';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import {
  sessionReplayApi,
  type SessionEventListItem,
  type SessionEventListParams,
} from '@/services/sessionReplay';

/** 由 startedAt/endedAt 推算时长（秒），返回可读字符串 */
const formatDuration = (startedAt?: string | null, endedAt?: string | null): string => {
  if (!startedAt || !endedAt) return '-';
  const start = dayjs(startedAt);
  const end = dayjs(endedAt);
  if (!start.isValid() || !end.isValid()) return '-';
  const seconds = end.diff(start, 'second');
  if (seconds < 0 || !Number.isFinite(seconds)) return '-';
  if (seconds < 60) return `${seconds}秒`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes < 60) return rest ? `${minutes}分${rest}秒` : `${minutes}分`;
  const hours = Math.floor(minutes / 60);
  const restMin = minutes % 60;
  return restMin ? `${hours}时${restMin}分` : `${hours}时`;
};

const SessionReplayListPage: React.FC = () => {
  const { actionRef } = useListPage();

  const columns: ProColumns<SessionEventListItem>[] = [
    {
      title: '会话ID',
      dataIndex: 'sessionId',
      width: 200,
      ellipsis: true,
      render: (_, record) => (
        <Typography.Text code copyable={{ text: record.sessionId }}>
          {record.sessionId.length > 20
            ? `${record.sessionId.slice(0, 8)}…${record.sessionId.slice(-8)}`
            : record.sessionId}
        </Typography.Text>
      ),
    },
    {
      title: '操作者',
      dataIndex: 'actorName',
      width: 120,
      search: false,
      render: (_, record) => record.actorName || record.actorId || '-',
    },
    {
      title: '平台',
      dataIndex: 'platform',
      valueType: 'select',
      valueEnum: {
        admin: { text: '管理端' },
        h5: { text: 'H5' },
        miniapp: { text: '小程序' },
      },
      hideInTable: true,
    },
    {
      title: '页面路径',
      dataIndex: 'pagePath',
      ellipsis: true,
      tooltip: '模糊匹配',
      render: (_, record) =>
        record.pagePath ? (
          <Tooltip title={record.pagePath}>
            <span>{record.pagePath}</span>
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: '事件数',
      dataIndex: 'eventCount',
      width: 90,
      search: false,
      align: 'right',
      sorter: false,
    },
    {
      title: '视口',
      dataIndex: 'viewportW',
      width: 110,
      search: false,
      render: (_, record) =>
        record.viewportW && record.viewportH ? `${record.viewportW}×${record.viewportH}` : '-',
    },
    {
      title: '开始时间',
      dataIndex: 'startedAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
      render: (_, record) => (record.startedAt ? dayjs(record.startedAt).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: '时长',
      key: 'duration',
      width: 100,
      search: false,
      render: (_, record) => formatDuration(record.startedAt, record.endedAt),
    },
    {
      title: '上报时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
      render: (_, record) => (record.createdAt ? dayjs(record.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: '时间范围',
      dataIndex: 'startTime',
      valueType: 'dateRange',
      hideInTable: true,
      search: {
        transform: (value: [string, string]) => {
          if (!value || value.length < 2) return {};
          return {
            startTime: dayjs(value[0]).startOf('day').toISOString(),
            endTime: dayjs(value[1]).endOf('day').toISOString(),
          };
        },
      },
    },
    {
      title: '操作者ID',
      dataIndex: 'actorId',
      hideInTable: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      fixed: 'right',
      search: false,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => history.push(`/session-replay/${record.sessionId}`)}
        >
          回放
        </Button>
      ),
    },
  ];

  return (
    <PageContainer
      header={{
        title: '会话回放',
        breadcrumb: {},
      }}
    >
      <ProTable<SessionEventListItem>
        actionRef={actionRef}
        rowKey="sessionId"
        columns={columns}
        scroll={{ x: 1200 }}
        search={{ labelWidth: 'auto', defaultCollapsed: false }}
        request={createListRequest<SessionEventListItem, SessionEventListParams>(
          (params) => sessionReplayApi.list(params),
          {
            // ProTable current/pageSize 已由 createListRequest 处理；
            // 这里只透传其余过滤字段（platform/actorId/pagePath/sessionId/startTime/endTime）
            paramTransform: (params) => {
              const { page, pageSize, platform, actorId, pagePath, sessionId, startTime, endTime } = params;
              const queryParams: SessionEventListParams = { page, pageSize };
              if (platform) queryParams.platform = platform;
              if (actorId) queryParams.actorId = actorId;
              if (pagePath) queryParams.pagePath = pagePath;
              if (sessionId) queryParams.sessionId = sessionId;
              if (startTime) queryParams.startTime = startTime;
              if (endTime) queryParams.endTime = endTime;
              return queryParams;
            },
            retryCount: 1,
          },
        )}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        options={{ density: false, fullScreen: false, reload: true, setting: false }}
      />
    </PageContainer>
  );
};

export default SessionReplayListPage;
