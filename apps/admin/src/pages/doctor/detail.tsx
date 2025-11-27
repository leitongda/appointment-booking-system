import { PageContainer, ProDescriptions } from '@ant-design/pro-components';
import { Avatar, Card, Tag } from 'antd';
import { useParams } from 'umi';

const DoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer title="医生详情">
      <Card>
        <ProDescriptions column={2}>
          <ProDescriptions.Item label="头像" span={2}>
            <Avatar size={64} />
          </ProDescriptions.Item>
          <ProDescriptions.Item label="姓名">张医生</ProDescriptions.Item>
          <ProDescriptions.Item label="工号">D001</ProDescriptions.Item>
          <ProDescriptions.Item label="职称">主任医师</ProDescriptions.Item>
          <ProDescriptions.Item label="所属科室">内科</ProDescriptions.Item>
          <ProDescriptions.Item label="挂号费">¥50.00</ProDescriptions.Item>
          <ProDescriptions.Item label="是否专家">
            <Tag color="gold">是</Tag>
          </ProDescriptions.Item>
          <ProDescriptions.Item label="状态">
            <Tag color="green">启用</Tag>
          </ProDescriptions.Item>
          <ProDescriptions.Item label="擅长领域" span={2}>
            心血管疾病、高血压、冠心病
          </ProDescriptions.Item>
          <ProDescriptions.Item label="医生简介" span={2}>
            从医20年，擅长心血管疾病的诊断与治疗...
          </ProDescriptions.Item>
        </ProDescriptions>
      </Card>
    </PageContainer>
  );
};

export default DoctorDetailPage;

