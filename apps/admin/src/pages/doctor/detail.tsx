import { PageContainer, ProDescriptions } from '@ant-design/pro-components';
import { Card, Avatar, Tag, Button, Space, Spin, Tabs } from 'antd';
import { 
  UserOutlined, 
  CalendarOutlined, 
  ScheduleOutlined,
} from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { history, useParams, useSearchParams } from '@umijs/max';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import DoctorScheduleTab from './components/DoctorScheduleTab';
import DoctorAppointmentTab from './components/DoctorAppointmentTab';

const DoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  
  // 从 URL 参数获取当前 tab，默认为 basic
  const activeTab = searchParams.get('tab') || 'basic';

  useEffect(() => {
    if (id) loadDoctor();
  }, [id]);

  const loadDoctor = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await doctorApi.getDetail(id);
      setDoctor(data);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (key: string) => {
    setSearchParams({ tab: key });
  };

  // 基本信息内容
  const BasicInfoContent = () => (
    <Card>
      <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
        <Avatar src={doctor?.avatar} size={100}>
          {doctor?.name?.charAt(0)}
        </Avatar>
        <div>
          <h2 style={{ margin: '0 0 8px' }}>{doctor?.name}</h2>
          <p style={{ color: '#666', margin: '0 0 8px' }}>{doctor?.title}</p>
          <Space>
            {doctor?.isRecommended === 1 && <Tag color="orange">推荐医生</Tag>}
            <Tag color={doctor?.status === 1 ? 'green' : 'default'}>
              {doctor?.status === 1 ? '在职' : '离职'}
            </Tag>
          </Space>
        </div>
      </div>
      <ProDescriptions column={2}>
        <ProDescriptions.Item label="所属科室">{doctor?.departmentName || '-'}</ProDescriptions.Item>
        <ProDescriptions.Item label="手机号">{doctor?.phone || '-'}</ProDescriptions.Item>
        <ProDescriptions.Item label="挂号费">¥{doctor?.registrationFee || 0}</ProDescriptions.Item>
        <ProDescriptions.Item label="排序">{doctor?.sortOrder || 0}</ProDescriptions.Item>
        <ProDescriptions.Item label="专长" span={2}>{doctor?.specialty || '-'}</ProDescriptions.Item>
        <ProDescriptions.Item label="简介" span={2}>{doctor?.introduction || '-'}</ProDescriptions.Item>
        <ProDescriptions.Item label="创建时间">{doctor?.createdAt}</ProDescriptions.Item>
        <ProDescriptions.Item label="更新时间">{doctor?.updatedAt || '-'}</ProDescriptions.Item>
      </ProDescriptions>
    </Card>
  );

  const tabItems = [
    {
      key: 'basic',
      label: (
        <span>
          <UserOutlined />
          基本信息
        </span>
      ),
      children: <BasicInfoContent />,
    },
    {
      key: 'schedule',
      label: (
        <span>
          <CalendarOutlined />
          排班管理
        </span>
      ),
      children: id ? (
        <DoctorScheduleTab doctorId={id} doctorName={doctor?.name} />
      ) : null,
    },
    {
      key: 'appointment',
      label: (
        <span>
          <ScheduleOutlined />
          预约记录
        </span>
      ),
      children: id ? (
        <DoctorAppointmentTab doctorId={id} doctorName={doctor?.name} />
      ) : null,
    },
  ];

  return (
    <PageContainer
      title={doctor?.name ? `${doctor.name} - 医生详情` : '医生详情'}
      extra={
        <Space>
          <Button onClick={() => history.push('/doctor/list')}>返回列表</Button>
          <Button type="primary" onClick={() => history.push(`/doctor/${id}/edit`)}>编辑</Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={tabItems}
          size="large"
          style={{ marginTop: -8 }}
        />
      </Spin>
    </PageContainer>
  );
};

export default DoctorDetailPage;
