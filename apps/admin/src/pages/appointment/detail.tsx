import { PageContainer, ProDescriptions } from '@ant-design/pro-components';
import { Card, Tag, Steps, Timeline } from 'antd';
import { useParams } from 'umi';

const AppointmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer title="预约详情">
      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <ProDescriptions column={3}>
          <ProDescriptions.Item label="预约单号">YY20241127001</ProDescriptions.Item>
          <ProDescriptions.Item label="状态">
            <Tag color="blue">已预约</Tag>
          </ProDescriptions.Item>
          <ProDescriptions.Item label="来源">小程序</ProDescriptions.Item>
          <ProDescriptions.Item label="预约日期">2024-11-28</ProDescriptions.Item>
          <ProDescriptions.Item label="时段">上午</ProDescriptions.Item>
          <ProDescriptions.Item label="队列号">5</ProDescriptions.Item>
          <ProDescriptions.Item label="挂号费">¥50.00</ProDescriptions.Item>
          <ProDescriptions.Item label="预约时间">2024-11-27 10:00:00</ProDescriptions.Item>
        </ProDescriptions>
      </Card>

      <Card title="就诊人信息" style={{ marginBottom: 16 }}>
        <ProDescriptions column={3}>
          <ProDescriptions.Item label="姓名">张三</ProDescriptions.Item>
          <ProDescriptions.Item label="手机号">138****8888</ProDescriptions.Item>
          <ProDescriptions.Item label="身份证">3101**********1234</ProDescriptions.Item>
        </ProDescriptions>
      </Card>

      <Card title="医生信息" style={{ marginBottom: 16 }}>
        <ProDescriptions column={3}>
          <ProDescriptions.Item label="医生">李医生</ProDescriptions.Item>
          <ProDescriptions.Item label="职称">主任医师</ProDescriptions.Item>
          <ProDescriptions.Item label="科室">内科</ProDescriptions.Item>
        </ProDescriptions>
      </Card>

      <Card title="状态流转">
        <Steps
          current={1}
          items={[
            { title: '已预约', description: '2024-11-27 10:00' },
            { title: '已签到', description: '等待签到' },
            { title: '候诊中', description: '' },
            { title: '就诊中', description: '' },
            { title: '已完成', description: '' },
          ]}
        />
      </Card>
    </PageContainer>
  );
};

export default AppointmentDetailPage;

