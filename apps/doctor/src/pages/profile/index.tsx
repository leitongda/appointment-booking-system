import { PageContainer, ProCard, ProForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormDigit } from '@ant-design/pro-components';
import { Button, message, Spin, Avatar, Descriptions, Tag } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';

const ProfilePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await doctorApi.getMyProfile();
      setDoctor(data);
    } catch (error: any) {
      message.error(error.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (values: any) => {
    try {
      const result = await doctorApi.updateMyProfile({
        title: values.title,
        specialty: values.specialty,
        introduction: values.introduction,
        gender: values.gender,
        yearsOfExperience: values.yearsOfExperience,
        education: values.education,
        graduateSchool: values.graduateSchool,
        licenseNumber: values.licenseNumber,
        honors: values.honors,
        scheduleDesc: values.scheduleDesc,
      });
      message.success('更新成功');
      setDoctor(result.doctor as Doctor);
      setEditing(false);
    } catch (error: any) {
      message.error(error.message || '更新失败');
    }
  };

  if (loading) {
    return (
      <PageContainer>
        <Spin spinning={true} style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
      </PageContainer>
    );
  }

  if (!doctor) {
    return (
      <PageContainer>
        <ProCard>加载失败</ProCard>
      </PageContainer>
    );
  }

  const genderMap: Record<number, string> = { 0: '未知', 1: '男', 2: '女' };

  return (
    <PageContainer>
      <ProCard>
        {editing ? (
          <ProForm
            onFinish={handleUpdate}
            initialValues={{
              title: doctor.title,
              specialty: doctor.specialty,
              introduction: doctor.introduction,
              gender: doctor.gender,
              yearsOfExperience: doctor.yearsOfExperience,
              education: doctor.education,
              graduateSchool: doctor.graduateSchool,
              licenseNumber: doctor.licenseNumber,
              honors: doctor.honors,
              scheduleDesc: doctor.scheduleDesc,
            }}
            submitter={{
              render: (_, dom) => (
                <div style={{ display: 'flex', gap: 8 }}>
                  {dom}
                  <Button onClick={() => setEditing(false)}>取消</Button>
                </div>
              ),
            }}
          >
            <ProCard title="基本信息" style={{ marginBottom: 16 }}>
              <ProFormText name="title" label="职称" placeholder="如：主任医师、副主任医师" />
              <ProFormSelect
                name="gender"
                label="性别"
                options={[
                  { label: '未知', value: 0 },
                  { label: '男', value: 1 },
                  { label: '女', value: 2 },
                ]}
              />
              <ProFormDigit name="yearsOfExperience" label="从业年限" min={0} max={60} />
              <ProFormText name="specialty" label="擅长" placeholder="如：心血管疾病、儿科常见病" />
            </ProCard>

            <ProCard title="教育背景" style={{ marginBottom: 16 }}>
              <ProFormText name="education" label="学历" placeholder="如：博士、硕士" />
              <ProFormText name="graduateSchool" label="毕业院校" />
              <ProFormText name="licenseNumber" label="执业证书编号" />
              <ProFormTextArea name="honors" label="荣誉/学术成就" placeholder="每行一条" />
            </ProCard>

            <ProCard title="个人介绍" style={{ marginBottom: 16 }}>
              <ProFormTextArea
                name="introduction"
                label="个人简介"
                placeholder="介绍您的专业背景、擅长领域等"
                fieldProps={{ rows: 4 }}
              />
              <ProFormTextArea
                name="scheduleDesc"
                label="出诊说明"
                placeholder="如：周一至周五上午出诊"
                fieldProps={{ rows: 2 }}
              />
            </ProCard>
          </ProForm>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
              <Avatar size={80} icon={<UserOutlined />} src={doctor.avatar} />
              <div style={{ marginLeft: 24 }}>
                <h2 style={{ margin: 0 }}>{doctor.name}</h2>
                <div style={{ color: '#666', marginTop: 4 }}>
                  {doctor.title && <Tag>{doctor.title}</Tag>}
                  {doctor.departmentName && <Tag color="blue">{doctor.departmentName}</Tag>}
                  {doctor.storeName && <Tag color="green">{doctor.storeName}</Tag>}
                </div>
              </div>
              <Button type="primary" style={{ marginLeft: 'auto' }} onClick={() => setEditing(true)}>
                编辑资料
              </Button>
            </div>

            <Descriptions column={2} bordered>
              <Descriptions.Item label="姓名">{doctor.name}</Descriptions.Item>
              <Descriptions.Item label="手机">{doctor.phone}</Descriptions.Item>
              <Descriptions.Item label="性别">{genderMap[doctor.gender || 0]}</Descriptions.Item>
              <Descriptions.Item label="从业年限">{doctor.yearsOfExperience ? `${doctor.yearsOfExperience}年` : '-'}</Descriptions.Item>
              <Descriptions.Item label="职称">{doctor.title || '-'}</Descriptions.Item>
              <Descriptions.Item label="擅长">{doctor.specialty || '-'}</Descriptions.Item>
              <Descriptions.Item label="学历">{doctor.education || '-'}</Descriptions.Item>
              <Descriptions.Item label="毕业院校">{doctor.graduateSchool || '-'}</Descriptions.Item>
              <Descriptions.Item label="执业证书编号">{doctor.licenseNumber || '-'}</Descriptions.Item>
              <Descriptions.Item label="所属科室">{doctor.departmentName || '-'}</Descriptions.Item>
              <Descriptions.Item label="所属门店">{doctor.storeName || '-'}</Descriptions.Item>
              <Descriptions.Item label="出诊说明">{doctor.scheduleDesc || '-'}</Descriptions.Item>
              <Descriptions.Item label="个人简介" span={2}>{doctor.introduction || '-'}</Descriptions.Item>
              <Descriptions.Item label="荣誉成就" span={2}>{doctor.honors || '-'}</Descriptions.Item>
            </Descriptions>
          </>
        )}
      </ProCard>
    </PageContainer>
  );
};

export default ProfilePage;
