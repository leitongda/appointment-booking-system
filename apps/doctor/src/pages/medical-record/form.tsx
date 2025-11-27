import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Card, message, Button, Space, Descriptions, Tag, Divider } from 'antd';
import { history, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';

const MedicalRecordFormPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const appointmentId = searchParams.get('appointmentId');
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (appointmentId) {
      loadAppointment();
    }
  }, [appointmentId]);

  const loadAppointment = async () => {
    try {
      const data = await appointmentApi.getDetail(appointmentId!);
      setAppointment(data);
    } catch (error) {
      message.error('加载预约信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      // TODO: 调用保存病历的 API
      console.log('提交病历:', { appointmentId, ...values });
      message.success('病历保存成功');
      history.push('/medical-record/list');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageContainer 
      title="填写病历"
      loading={loading}
      extra={
        <Button onClick={() => history.push('/consultation')}>返回就诊</Button>
      }
    >
      {appointment && (
        <Card title="患者信息" style={{ marginBottom: 16 }}>
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
            <Descriptions.Item label="患者姓名">{appointment.patientName}</Descriptions.Item>
            <Descriptions.Item label="手机号">
              {appointment.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
            </Descriptions.Item>
            <Descriptions.Item label="就诊时间">
              {appointment.scheduleDate} {TIME_SLOT_MAP[appointment.timeSlot || 'AM']}
            </Descriptions.Item>
            <Descriptions.Item label="预约单号">{appointment.appointmentNo}</Descriptions.Item>
            <Descriptions.Item label="队列号">
              <Tag color="blue">第{appointment.queueNumber}号</Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card title="病历内容">
        <ProForm
          onFinish={handleSubmit}
          submitter={{
            render: (props, doms) => (
              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Space size="large">
                  <Button size="large" onClick={() => history.back()}>取消</Button>
                  <Button 
                    type="primary" 
                    size="large" 
                    loading={submitting}
                    onClick={() => props.form?.submit()}
                  >
                    保存病历
                  </Button>
                </Space>
              </div>
            ),
          }}
        >
          <ProFormTextArea
            name="chiefComplaint"
            label="主诉"
            placeholder="请输入患者主诉，如：头痛3天"
            rules={[{ required: true, message: '请输入主诉' }]}
            fieldProps={{ rows: 2 }}
          />
          
          <ProFormTextArea
            name="presentIllness"
            label="现病史"
            placeholder="请详细描述发病经过、症状特点、伴随症状等"
            fieldProps={{ rows: 4 }}
          />
          
          <ProFormTextArea
            name="pastHistory"
            label="既往史"
            placeholder="请描述既往疾病史、手术史、过敏史等"
            fieldProps={{ rows: 2 }}
          />

          <Divider />
          
          <ProFormTextArea
            name="physicalExam"
            label="体格检查"
            placeholder="请输入体格检查结果"
            fieldProps={{ rows: 3 }}
          />
          
          <ProFormTextArea
            name="auxiliaryExam"
            label="辅助检查"
            placeholder="请输入辅助检查结果（如：血常规、影像等）"
            fieldProps={{ rows: 2 }}
          />

          <Divider />
          
          <ProFormTextArea
            name="diagnosis"
            label="诊断"
            placeholder="请输入诊断结果"
            rules={[{ required: true, message: '请输入诊断' }]}
            fieldProps={{ rows: 2 }}
          />
          
          <ProFormTextArea
            name="treatment"
            label="治疗方案"
            placeholder="请输入治疗方案"
            fieldProps={{ rows: 3 }}
          />

          <Divider />
          
          <ProFormTextArea
            name="prescription"
            label="处方"
            placeholder="请输入处方内容，格式如：&#10;1. 药品名称 用法用量&#10;2. 药品名称 用法用量"
            fieldProps={{ rows: 4 }}
          />
          
          <ProFormTextArea
            name="advice"
            label="医嘱"
            placeholder="请输入医嘱，如：注意休息、清淡饮食、定期复查等"
            fieldProps={{ rows: 2 }}
          />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default MedicalRecordFormPage;
