import { Modal, Table, Tag } from 'antd';
import dayjs from 'dayjs';

interface HistoryLog {
  id: string;
  actionType: string;
  operatorName: string;
  startDate?: string;
  endDate?: string;
  affectedCount: number;
  createdAt: string;
  remark?: string;
}

interface HistoryLogsModalProps {
  open: boolean;
  onCancel: () => void;
  logs: HistoryLog[];
  loading: boolean;
  templateName?: string;
}

const ACTION_TYPE_MAP: Record<string, { text: string; color: string }> = {
  generate: { text: '生成排班', color: 'green' },
  delete: { text: '删除排班', color: 'red' },
  suspend: { text: '批量停诊', color: 'orange' },
};

const HistoryLogsModal: React.FC<HistoryLogsModalProps> = ({
  open,
  onCancel,
  logs,
  loading,
  templateName,
}) => {
  const columns = [
    {
      title: '操作类型',
      dataIndex: 'actionType',
      width: 100,
      render: (type: string) => {
        const info = ACTION_TYPE_MAP[type] || { text: type, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '操作人',
      dataIndex: 'operatorName',
      width: 100,
    },
    {
      title: '日期范围',
      width: 180,
      render: (_: any, record: HistoryLog) => {
        if (record.startDate && record.endDate) {
          return `${record.startDate} ~ ${record.endDate}`;
        }
        return record.startDate || record.endDate || '-';
      },
    },
    {
      title: '影响记录数',
      dataIndex: 'affectedCount',
      width: 100,
    },
    {
      title: '操作时间',
      dataIndex: 'createdAt',
      width: 160,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
    },
  ];

  return (
    <Modal
      title={`历史记录 - ${templateName || ''}`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={1300}
    >
      <Table
        columns={columns}
        dataSource={logs}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        size="small"
        locale={{ emptyText: '暂无历史记录' }}
      />
    </Modal>
  );
};

export default HistoryLogsModal;
