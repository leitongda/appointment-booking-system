import { PageContainer, ProTable, StatisticCard } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Row, Col, Card, Modal } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';

const { Statistic } = StatisticCard;

const AppointmentListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [statistics, setStatistics] = useState({ total: 0, pending: 0, completed: 0, cancelled: 0 });
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<Appointment | null>(null);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    try {
      const data = await appointmentApi.getStatistics();
      setStatistics(data);
    } catch (error) {
      console.error('加载统计失败', error);
    }
  };

  const handleViewDetail = (record: Appointment) => {
    setCurrentRecord(record);
    setDetailVisible(true);
  };

  const columns: ProColumns<Appointment>[] = [
    { title: '预约单号', dataIndex: 'appointmentNo', width: 150, copyable: true },
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    { title: '患者手机', dataIndex: 'patientPhone', width: 130, search: false },
    { title: '医生', dataIndex: 'doctorName', width: 100 },
    { title: '科室', dataIndex: 'departmentName', width: 120, search: false },
    { title: '预约日期', dataIndex: 'scheduleDate', width: 120, valueType: 'date' },
    { title: '时段', dataIndex: 'timeSlot', width: 80, render: (_, r) => TIME_SLOT_MAP[r.timeSlot], valueEnum: TIME_SLOT_MAP },
    { title: '队列号', dataIndex: 'queueNumber', width: 80, search: false, render: (_, r) => r.queueNumber ? <Tag color="blue">第{r.queueNumber}号</Tag> : '-' },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      valueEnum: APPOINTMENT_STATUS_MAP,
      render: (_, r) => <Tag color={APPOINTMENT_STATUS_COLOR[r.status]}>{APPOINTMENT_STATUS_MAP[r.status]}</Tag>
    },
    { title: '预约时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option',
      width: 100,
      render: (_, record) => (
        <Space>
          <a onClick={() => handleViewDetail(record)}>详情</a>
        </Space>
      )
    },
  ];

  return (
    <PageContainer>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="总预约" value={statistics.total} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="待就诊" value={statistics.pending} valueStyle={{ color: '#1890ff' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="已完成" value={statistics.completed} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="已取消" value={statistics.cancelled} valueStyle={{ color: '#999' }} /></Card>
        </Col>
      </Row>

      <ProTable<Appointment>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const { current, pageSize, appointmentNo, patientName, status, scheduleDate } = params;
          const result = await appointmentApi.getList({
            status,
            startDate: scheduleDate,
            page: current,
            pageSize,
          });
          return { data: result.data, success: true, total: result.total };
        }}
      />

      <Modal
        title="预约详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={600}
      >
        {currentRecord && (
          <div>
            <p><strong>预约单号：</strong>{currentRecord.appointmentNo}</p>
            <p><strong>患者姓名：</strong>{currentRecord.patientName}</p>
            <p><strong>患者手机：</strong>{currentRecord.patientPhone}</p>
            <p><strong>医生：</strong>{currentRecord.doctorName}</p>
            <p><strong>科室：</strong>{currentRecord.departmentName}</p>
            <p><strong>预约日期：</strong>{currentRecord.scheduleDate} {TIME_SLOT_MAP[currentRecord.timeSlot]}</p>
            <p><strong>队列号：</strong>第{currentRecord.queueNumber}号</p>
            <p><strong>状态：</strong><Tag color={APPOINTMENT_STATUS_COLOR[currentRecord.status]}>{APPOINTMENT_STATUS_MAP[currentRecord.status]}</Tag></p>
            {currentRecord.signInTime && <p><strong>签到时间：</strong>{currentRecord.signInTime}</p>}
            {currentRecord.cancelTime && <p><strong>取消时间：</strong>{currentRecord.cancelTime}</p>}
            {currentRecord.cancelReason && <p><strong>取消原因：</strong>{currentRecord.cancelReason}</p>}
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default AppointmentListPage;
