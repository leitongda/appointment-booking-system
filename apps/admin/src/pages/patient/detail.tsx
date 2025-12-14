import { PageContainer, ProDescriptions, ProTable } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  Card,
  Tag,
  Button,
  Space,
  Spin,
  Tabs,
  Avatar,
  Typography,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  InputNumber,
  Input,
  Select,
  DatePicker,
  App,
  Table,
} from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { useEffect, useState, useRef } from 'react';
import { history, useParams } from '@umijs/max';
import { patientApi, doctorApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type {
  PatientDetail,
  PatientAppointment,
  ConsumptionRecord,
  PointLog,
  PatientListItem,
} from '@hospital/api';
import type { Doctor } from '@hospital/shared';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// 来源映射
const SOURCE_MAP: Record<number, string> = {
  1: '用户添加',
  2: '管理员添加',
};

// 证件类型映射
const ID_CARD_TYPE_MAP: Record<number, string> = {
  1: '居民身份证（户口簿）',
  2: '户口簿',
  3: '护照',
};

// 预约状态映射
const APPOINTMENT_STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待支付', color: 'gold' },
  1: { text: '待就诊', color: 'blue' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '就诊中', color: 'processing' },
  4: { text: '已完成', color: 'green' },
  5: { text: '已就诊', color: 'green' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已爽约', color: 'red' },
};

// 积分类型映射
const POINT_TYPE_MAP: Record<number, string> = {
  1: '消费',
  2: '充值',
  3: '赠送',
  4: '手动调整',
};

const PatientDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [activeTab, setActiveTab] = useState('profile');
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [pointModalOpen, setPointModalOpen] = useState(false);
  const [pointForm] = Form.useForm();
  const appointmentRef = useRef<ActionType>();
  const consumptionRef = useRef<ActionType>();
  const pointRef = useRef<ActionType>();

  useEffect(() => {
    if (id) {
      loadPatient();
      loadDoctors();
    }
  }, [id]);

  const loadPatient = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await patientApi.getDetail(id);
      setPatient(data);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDoctors = async () => {
    try {
      const res = await doctorApi.getList({ pageSize: 100 });
      setDoctors(res.data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const handleAdjustPoints = async (values: { amount: number; remark: string }) => {
    if (!id) return;
    try {
      await patientApi.adjustPoints(id, values);
      message.success('积分调整成功');
      setPointModalOpen(false);
      pointForm.resetFields();
      loadPatient();
      pointRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '积分调整失败');
    }
  };

  // 预约记录列定义
  const appointmentColumns: ProColumns<PatientAppointment>[] = [
    { title: '门店名称', dataIndex: 'storeName', width: 120, ellipsis: true, search: false },
    { title: '科室名称', dataIndex: 'departmentName', width: 100, search: false },
    {
      title: '医生姓名',
      dataIndex: 'doctorId',
      width: 100,
      valueType: 'select',
      fieldProps: {
        options: doctors.map((d) => ({ label: d.name, value: d.id })),
        placeholder: '全部',
      },
      render: (_, record) => record.doctorName || '-',
    },
    {
      title: '预约日期',
      dataIndex: 'dateRange',
      valueType: 'dateRange',
      width: 200,
      search: {
        transform: (value) => ({
          startDate: value?.[0],
          endDate: value?.[1],
        }),
      },
      render: (_, record) => record.scheduleDate || '-',
    },
    { title: '开始时间', dataIndex: 'startTime', width: 90, search: false },
    { title: '结束时间', dataIndex: 'endTime', width: 90, search: false },
    {
      title: '管理员代预约',
      dataIndex: 'isAdminBooked',
      width: 110,
      search: false,
      render: (_, record) => (record.isAdminBooked ? '是' : '否'),
    },
    {
      title: '是否复诊',
      dataIndex: 'isFollowUp',
      width: 90,
      search: false,
      render: (_, record) => (record.isFollowUp ? '是' : '否'),
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueType: 'select',
      valueEnum: {
        0: '待支付',
        1: '待就诊',
        4: '已就诊',
        6: '已取消',
        7: '退款中',
      },
      render: (_, record) => {
        const s = APPOINTMENT_STATUS_MAP[record.status] || { text: '未知', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 60,
      render: (_, record) => (
        <a onClick={() => history.push(`/appointment/${record.id}`)}>详情</a>
      ),
    },
  ];

  // 项目记录列定义
  const consumptionColumns: ProColumns<ConsumptionRecord>[] = [
    { title: '订单号', dataIndex: 'orderNo', width: 160, copyable: true, search: false },
    { title: '门店名称', dataIndex: 'storeName', width: 120, search: false },
    {
      title: '项目名称',
      dataIndex: 'itemName',
      width: 150,
      valueType: 'select',
      fieldProps: { placeholder: '全部' },
    },
    { title: '预约日期', dataIndex: 'scheduleDate', width: 110, search: false },
    { title: '开始时间', dataIndex: 'startTime', width: 90, search: false },
    { title: '结束时间', dataIndex: 'endTime', width: 90, search: false },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      search: false,
      render: (_, record) => {
        const s = APPOINTMENT_STATUS_MAP[record.status] || { text: '未知', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 60,
      render: (_, record) => <a onClick={() => history.push(`/appointment/${record.id}`)}>详情</a>,
    },
  ];

  // 积分流水列定义
  const pointColumns: ProColumns<PointLog>[] = [
    { title: 'ID', dataIndex: 'id', width: 280, ellipsis: true },
    { title: '时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160 },
    {
      title: '积分变更',
      dataIndex: 'changeAmount',
      width: 100,
      render: (_, record) => (
        <span style={{ color: record.changeAmount >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {record.changeAmount >= 0 ? '+' : ''}
          {record.changeAmount}
        </span>
      ),
    },
    { title: '剩余积分', dataIndex: 'balance', width: 100 },
    { title: '备注', dataIndex: 'remark', width: 200, ellipsis: true },
    { title: '操作人', dataIndex: 'operatorName', width: 100 },
  ];

  // 家庭成员列定义
  const familyColumns = [
    { title: '姓名', dataIndex: 'name', key: 'name', width: 80 },
    {
      title: '性别',
      dataIndex: 'gender',
      key: 'gender',
      width: 60,
      render: (val: number) => (val === 1 ? '男' : val === 2 ? '女' : '-'),
    },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120 },
    { title: '关系', dataIndex: 'relationship', key: 'relationship', width: 80 },
    {
      title: '默认',
      dataIndex: 'isDefault',
      key: 'isDefault',
      width: 60,
      render: (val: boolean) => (val ? <Tag color="blue">默认</Tag> : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 60,
      render: (_: any, record: PatientListItem) => (
        <a onClick={() => history.push(`/patient/${record.id}`)}>查看</a>
      ),
    },
  ];

  // 计算家庭成员总消费
  const familyTotalConsumption = patient?.familyMembers?.reduce((sum, m) => sum, 0) || 0;

  const tabItems = [
    {
      key: 'profile',
      label: '档案详情',
      children: (
        <Card>
          <ProDescriptions column={2}>
            <ProDescriptions.Item label="用户昵称">{patient?.nickname || '微信用户'}</ProDescriptions.Item>
            <ProDescriptions.Item label="姓名">{patient?.name}</ProDescriptions.Item>
            <ProDescriptions.Item label="联系电话">{patient?.phone}</ProDescriptions.Item>
            <ProDescriptions.Item label="性别">
              {patient?.gender === 1 ? '男' : patient?.gender === 2 ? '女' : '-'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="省/市/区">
              {[patient?.province, patient?.city, patient?.district].filter(Boolean).join('/') || '-'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="街道/社区">{patient?.street || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="就诊卡编号">{patient?.cardNo || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="证件类型">
              {ID_CARD_TYPE_MAP[patient?.idCardType || 1] || '-'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="证件号">{patient?.idCard || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="民族">{patient?.ethnicity || '汉族'}</ProDescriptions.Item>
            <ProDescriptions.Item label="出生日期">{patient?.birthday || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="年龄">{patient?.age ?? '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="关系">{patient?.relationship || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="详细地址" span={2}>{patient?.address || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="来源">{SOURCE_MAP[patient?.source || 1] || '-'}</ProDescriptions.Item>
          </ProDescriptions>
        </Card>
      ),
    },
    {
      key: 'appointments',
      label: '预约记录',
      children: (
        <ProTable<PatientAppointment>
          actionRef={appointmentRef}
          rowKey="id"
          columns={appointmentColumns}
          scroll={{ x: 1400 }}
          request={async (params) => {
            if (!id) return { data: [], total: 0, success: true };
            const { current, pageSize, doctorId, startDate, endDate, status, ...rest } = params;
            return toProTableResult(
              await patientApi.getAppointments(id, {
                ...rest,
                doctorId,
                startDate,
                endDate,
                status,
                page: current,
                pageSize,
              })
            );
          }}
          pagination={{ defaultPageSize: 10, showSizeChanger: true }}
          search={{ labelWidth: 'auto' }}
          toolBarRender={() => [
            <Button key="export" onClick={() => message.info('导出功能开发中')}>
              导出
            </Button>,
          ]}
        />
      ),
    },
    {
      key: 'consumption',
      label: '项目记录',
      children: (
        <ProTable<ConsumptionRecord>
          actionRef={consumptionRef}
          rowKey="id"
          columns={consumptionColumns}
          scroll={{ x: 1100 }}
          request={async (params) => {
            if (!id) return { data: [], total: 0, success: true };
            const { current, pageSize, itemName, ...rest } = params;
            return toProTableResult(
              await patientApi.getConsumptionRecords(id, {
                ...rest,
                itemName,
                page: current,
                pageSize,
              })
            );
          }}
          pagination={{ defaultPageSize: 10, showSizeChanger: true }}
          search={{ labelWidth: 'auto' }}
          toolBarRender={() => [
            <Button key="export" onClick={() => message.info('导出功能开发中')}>
              导出
            </Button>,
          ]}
        />
      ),
    },
    {
      key: 'points',
      label: '积分',
      children: (
        <div>
          <Card style={{ marginBottom: 16 }}>
            <Row gutter={24} align="middle">
              <Col>
                <Space size="large">
                  <Avatar size={64} icon={<UserOutlined />} />
                  <div>
                    <Title level={5} style={{ margin: 0 }}>
                      {patient?.name}
                    </Title>
                    <Text type="secondary">
                      {patient?.gender === 1 ? '男' : patient?.gender === 2 ? '女' : ''} {patient?.phone}
                    </Text>
                  </div>
                </Space>
              </Col>
              <Col flex="auto" style={{ textAlign: 'right' }}>
                <Space size="large">
                  <Statistic title="当前积分" value={patient?.points || 0} />
                  <Button type="primary" onClick={() => setPointModalOpen(true)}>
                    调整积分
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
          <Card title="积分流水">
            <ProTable<PointLog>
              actionRef={pointRef}
              rowKey="id"
              columns={pointColumns}
              search={false}
              request={async (params) => {
                if (!id) return { data: [], total: 0, success: true };
                const { current, pageSize } = params;
                const result = await patientApi.getPointLogs(id, { page: current, pageSize });
                return {
                  data: result.data,
                  total: result.total,
                  success: true,
                };
              }}
              pagination={{ defaultPageSize: 10, showSizeChanger: true }}
            />
          </Card>
        </div>
      ),
    },
  ];

  return (
    <PageContainer
      title="患者详情"
      extra={<Button onClick={() => history.push('/patient/list')}>返回列表</Button>}
    >
      <Spin spinning={loading}>
        {/* 头部信息卡片 */}
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={24} align="middle">
            <Col>
              <Space size="large">
                <Avatar size={80} icon={<UserOutlined />} />
                <div>
                  <Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {patient?.name}
                    </Title>
                    <Text>{patient?.gender === 1 ? '男' : patient?.gender === 2 ? '女' : ''}</Text>
                    <Text>{patient?.phone}</Text>
                    <Tag>{SOURCE_MAP[patient?.source || 1]}</Tag>
                    {patient?.isBlacklist && <Tag color="red">黑名单</Tag>}
                  </Space>
                  <div style={{ marginTop: 8 }}>
                    <Space size="large">
                      <Text type="secondary">
                        累计消费: <Text strong>¥{patient?.totalConsumption?.toFixed(2) || '0.00'}</Text>
                      </Text>
                      <Text type="secondary">
                        最近就诊: <Text>{patient?.lastVisitDate || '暂无记录'}</Text>
                      </Text>
                    </Space>
                  </div>
                </div>
              </Space>
            </Col>
          </Row>
        </Card>

        {/* Tab 内容 */}
        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </Card>

        {/* 家庭成员卡片 */}
        <Card
          title={`家庭成员 总消费：¥${familyTotalConsumption.toFixed(2)}`}
          style={{ marginTop: 16 }}
        >
          <Table
            dataSource={patient?.familyMembers || []}
            columns={familyColumns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </Card>
      </Spin>

      {/* 积分调整弹窗 */}
      <Modal
        title="调整积分"
        open={pointModalOpen}
        onCancel={() => {
          setPointModalOpen(false);
          pointForm.resetFields();
        }}
        onOk={() => pointForm.submit()}
        destroyOnClose
      >
        <Form form={pointForm} layout="vertical" onFinish={handleAdjustPoints}>
          <Form.Item
            name="amount"
            label="调整积分"
            rules={[{ required: true, message: '请输入调整积分' }]}
            extra="正数为增加，负数为减少"
          >
            <InputNumber style={{ width: '100%' }} placeholder="请输入调整积分数量" />
          </Form.Item>
          <Form.Item
            name="remark"
            label="调整原因"
            rules={[{ required: true, message: '请输入调整原因' }]}
          >
            <Input.TextArea rows={3} placeholder="请输入调整原因" maxLength={200} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default PatientDetailPage;
