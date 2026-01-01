import { useRef, useState, useEffect } from 'react';
import { Card, Row, Col, Tag, Space, Popconfirm } from 'antd';
import { 
  ClockCircleOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable, StatisticCard } from '@ant-design/pro-components';
import { history, useAccess } from '@umijs/max';
import { appointmentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Appointment, AppointmentStatistics } from '@hospital/shared';

interface DoctorAppointmentTabProps {
  doctorId: string;
  doctorName?: string;
}

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待支付', color: 'orange' },
  1: { text: '已预约', color: 'blue' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '候诊中', color: 'purple' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'green' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已过期', color: 'default' },
  8: { text: '已关闭', color: 'default' },
};

const DoctorAppointmentTab: React.FC<DoctorAppointmentTabProps> = ({ doctorId, doctorName }) => {
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [statistics, setStatistics] = useState<AppointmentStatistics | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  useEffect(() => {
    loadStatistics();
  }, [doctorId]);

  const loadStatistics = async () => {
    if (!doctorId) return;
    
    setLoadingStats(true);
    try {
      const data = await appointmentApi.getStatistics({ doctorId });
      setStatistics(data);
    } catch (error) {
      console.error('加载统计失败', error);
    } finally {
      setLoadingStats(false);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await appointmentApi.cancel(id, '管理员取消');
      actionRef.current?.reload();
      loadStatistics();
    } catch (error) {
      console.error('取消失败', error);
    }
  };

  const handleMarkNoShow = async (id: string) => {
    try {
      await appointmentApi.markNoShow(id);
      actionRef.current?.reload();
      loadStatistics();
    } catch (error) {
      console.error('标记爽约失败', error);
    }
  };

  const columns: ProColumns<Appointment>[] = [
    {
      title: '预约编号',
      dataIndex: 'appointmentNo',
      width: 140,
      copyable: true,
    },
    {
      title: '患者',
      dataIndex: 'patientName',
      width: 80,
    },
    {
      title: '手机号',
      dataIndex: 'patientPhone',
      width: 120,
      search: false,
    },
    {
      title: '预约日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 70,
      valueEnum: {
        morning: '上午',
        afternoon: '下午',
        evening: '晚上',
      },
    },
    {
      title: '排队号',
      dataIndex: 'queueNumber',
      width: 70,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, record) => {
        const status = STATUS_MAP[record.status] || { text: '未知', color: 'default' };
        return <Tag color={status.color}>{status.text}</Tag>;
      },
    },
    {
      title: '预约时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 130,
      render: (_, record) => (
        <Space>
          {access.hasPermission?.('appointment:detail') && (
            <a onClick={() => history.push(`/appointment/${record.id}`)}>详情</a>
          )}
          {record.status === 0 && (
            <>
              {access.hasPermission?.('appointment:cancel') && (
                <Popconfirm title="确定取消该预约吗？" onConfirm={() => handleCancel(record.id)}>
                  <a style={{ color: '#ff4d4f' }}>取消</a>
                </Popconfirm>
              )}
              {access.hasPermission?.('appointment:update') && (
                <Popconfirm title="确定标记为爽约吗？" onConfirm={() => handleMarkNoShow(record.id)}>
                  <a style={{ color: '#fa8c16' }}>爽约</a>
                </Popconfirm>
              )}
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <StatisticCard
            loading={loadingStats}
            statistic={{
              title: '总预约数',
              value: statistics?.total ?? 0,
              icon: <ClockCircleOutlined style={{ color: '#1890ff' }} />,
            }}
          />
        </Col>
        <Col span={6}>
          <StatisticCard
            loading={loadingStats}
            statistic={{
              title: '待就诊',
              value: (statistics?.pending ?? 0) + (statistics?.signedIn ?? 0),
              icon: <ClockCircleOutlined style={{ color: '#faad14' }} />,
            }}
          />
        </Col>
        <Col span={6}>
          <StatisticCard
            loading={loadingStats}
            statistic={{
              title: '已完成',
              value: statistics?.completed ?? 0,
              icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
            }}
          />
        </Col>
        <Col span={6}>
          <StatisticCard
            loading={loadingStats}
            statistic={{
              title: '取消/爽约',
              value: (statistics?.cancelled ?? 0) + (statistics?.noShow ?? 0),
              icon: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
            }}
          />
        </Col>
      </Row>

      {/* 预约列表 */}
      <Card title={doctorName ? `${doctorName} 的预约记录` : '预约记录'}>
        <ProTable<Appointment>
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={async (params) => {
            const { current, pageSize, scheduleDate, ...rest } = params;
            return toProTableResult(
              await appointmentApi.getList({
                ...rest,
                doctorId,
                startDate: scheduleDate,
                endDate: scheduleDate,
                page: current,
                pageSize,
              })
            );
          }}
          pagination={{ defaultPageSize: 10 }}
          search={{ 
            labelWidth: 'auto',
            collapsed: false,
            collapseRender: false,
          }}
          options={false}
          dateFormatter="string"
        />
      </Card>
    </div>
  );
};

export default DoctorAppointmentTab;

