import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormDigit } from '@ant-design/pro-components';
import { Card, message, Button, Space, Descriptions, Tag, Divider, Upload, List, Popconfirm } from 'antd';
import { UploadOutlined, DeleteOutlined, FileOutlined, FilePdfOutlined, FileImageOutlined } from '@ant-design/icons';
import { history, useSearchParams } from 'umi';
import { useState, useEffect, useRef } from 'react';
import { appointmentApi, medicalRecordApi, examinationReportApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import type { ExaminationReportListItem } from '@hospital/api';
import type { ProFormInstance } from '@ant-design/pro-components';
import type { UploadFile } from 'antd';

const MedicalRecordFormPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const appointmentId = searchParams.get('appointmentId');
  const recordId = searchParams.get('recordId');
  const isEdit = !!recordId;
  const formRef = useRef<ProFormInstance>();
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [record, setRecord] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [reports, setReports] = useState<ExaminationReportListItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  useEffect(() => {
    loadData();
  }, [appointmentId, recordId]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (recordId) {
        // 编辑模式：加载病历详情
        const recordData = await medicalRecordApi.getDetail(recordId);
        setRecord(recordData);

        // 如果病历已提交（status=2），不允许编辑
        if (recordData.status === 2) {
          message.warning('已提交的病历不允许编辑');
          history.push('/medical-record/list');
          return;
        }

        // 加载关联的预约信息
        if (recordData.appointmentId) {
          const appointmentData = await appointmentApi.getDetail(recordData.appointmentId);
          setAppointment(appointmentData);
        }

        // 填充表单
        setTimeout(() => {
          formRef.current?.setFieldsValue({
            chiefComplaint: recordData.chiefComplaint,
            presentIllness: recordData.presentIllness,
            pastHistory: recordData.pastHistory,
            allergyHistory: recordData.allergyHistory,
            familyHistory: recordData.familyHistory,
            medicationHistory: recordData.medicationHistory,
            physicalExam: recordData.physicalExam,
            auxiliaryExam: recordData.auxiliaryExam,
            diagnosis: recordData.diagnosis,
            treatment: recordData.treatment,
            prescription: recordData.prescription,
            advice: recordData.advice,
            totalFee: recordData.totalFee,
          });
        }, 100);
      } else if (appointmentId) {
        // 新建模式：加载预约信息
        const data = await appointmentApi.getDetail(appointmentId);
        setAppointment(data);
      }
    } catch (error) {
      message.error('加载信息失败');
    } finally {
      setLoading(false);
    }
  };

  const loadReports = async () => {
    if (!appointmentId && !recordId) return;
    try {
      let data: ExaminationReportListItem[] = [];
      if (recordId) {
        data = await examinationReportApi.getByRecord(recordId);
      } else if (appointmentId) {
        data = await examinationReportApi.getByAppointment(appointmentId);
      }
      setReports(data);
    } catch (error) {
      console.error('加载检查报告失败:', error);
    }
  };

  const handleUpload = async (file: File) => {
    if (!appointmentId) {
      message.error('缺少预约ID');
      return false;
    }

    // 校验文件类型
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      message.error('仅支持 PDF、JPEG、PNG、WebP 格式');
      return false;
    }

    // 校验文件大小 (20MB)
    if (file.size > 20 * 1024 * 1024) {
      message.error('文件大小不能超过 20MB');
      return false;
    }

    setUploading(true);
    try {
      await examinationReportApi.upload({
        file,
        appointmentId,
        recordId: recordId || undefined,
        reportType: file.type === 'application/pdf' ? 'imaging' : 'imaging',
        title: file.name.replace(/\.[^/.]+$/, ''),
      });
      message.success('报告上传成功');
      loadReports();
    } catch (error: any) {
      message.error(error.message || '上传失败');
    } finally {
      setUploading(false);
    }
    return false; // 阻止自动上传
  };

  const handleDeleteReport = async (reportId: string) => {
    try {
      await examinationReportApi.delete(reportId);
      message.success('报告已删除');
      loadReports();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const getFileIcon = (fileType: string) => {
    if (fileType === 'application/pdf') return <FilePdfOutlined style={{ color: '#ff4d4f' }} />;
    if (fileType.startsWith('image/')) return <FileImageOutlined style={{ color: '#1890ff' }} />;
    return <FileOutlined />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  useEffect(() => {
    loadReports();
  }, [appointmentId, recordId]);

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      if (isEdit && recordId) {
        // 编辑模式：更新病历
        await medicalRecordApi.update(recordId, {
          chiefComplaint: values.chiefComplaint,
          presentIllness: values.presentIllness,
          pastHistory: values.pastHistory,
          allergyHistory: values.allergyHistory,
          familyHistory: values.familyHistory,
          medicationHistory: values.medicationHistory,
          physicalExam: values.physicalExam,
          auxiliaryExam: values.auxiliaryExam,
          diagnosis: values.diagnosis,
          treatment: values.treatment,
          prescription: values.prescription,
          advice: values.advice,
          totalFee: values.totalFee,
          status: values.status || record?.status || 1,
        });
        message.success('病历更新成功');
      } else if (appointmentId) {
        // 新建模式：创建病历
        await medicalRecordApi.create({
          appointmentId,
          chiefComplaint: values.chiefComplaint,
          presentIllness: values.presentIllness,
          pastHistory: values.pastHistory,
          allergyHistory: values.allergyHistory,
          familyHistory: values.familyHistory,
          medicationHistory: values.medicationHistory,
          physicalExam: values.physicalExam,
          auxiliaryExam: values.auxiliaryExam,
          diagnosis: values.diagnosis,
          treatment: values.treatment,
          prescription: values.prescription,
          advice: values.advice,
          totalFee: values.totalFee,
          status: values.status || 2,
        });
        message.success('病历保存成功');
      } else {
        message.error('缺少必要参数');
        return;
      }
      history.push('/medical-record/list');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageContainer
      title={isEdit ? '编辑病历' : '填写病历'}
      loading={loading}
      extra={
        <Button onClick={() => history.back()}>返回</Button>
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
              {appointment.scheduleDate} {TIME_SLOT_MAP[appointment.timeSlot || 'morning']}
            </Descriptions.Item>
            <Descriptions.Item label="预约单号">{appointment.appointmentNo}</Descriptions.Item>
            <Descriptions.Item label="队列号">
              <Tag color="blue">第{appointment.queueNumber}号</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="科室">{appointment.departmentName}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card title="病历内容">
        <ProForm
          formRef={formRef}
          onFinish={handleSubmit}
          submitter={{
            render: (props, doms) => (
              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Space size="large">
                  <Button size="large" onClick={() => history.back()}>取消</Button>
                  <Button 
                    size="large" 
                    onClick={() => {
                      props.form?.setFieldValue('status', 1);
                      props.form?.submit();
                    }}
                  >
                    保存草稿
                  </Button>
                  <Button 
                    type="primary" 
                    size="large" 
                    loading={submitting}
                    onClick={() => {
                      props.form?.setFieldValue('status', 2);
                      props.form?.submit();
                    }}
                  >
                    提交病历
                  </Button>
                </Space>
              </div>
            ),
          }}
        >
          <ProFormText name="status" hidden initialValue={2} />
          
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
            placeholder="请描述既往疾病史、手术史等"
            fieldProps={{ rows: 2 }}
          />

          <ProFormTextArea
            name="allergyHistory"
            label="过敏史"
            placeholder="请描述药物过敏、食物过敏等情况"
            fieldProps={{ rows: 2 }}
          />

          <ProFormTextArea
            name="familyHistory"
            label="家族史"
            placeholder="请描述家族遗传病史、家族成员重大疾病等"
            fieldProps={{ rows: 2 }}
          />

          <ProFormTextArea
            name="medicationHistory"
            label="用药史"
            placeholder="请描述当前及近期用药情况，包括药物名称、剂量、频率等"
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

          {/* 检查报告上传 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>检查报告文件</div>
            <Upload
              beforeUpload={handleUpload}
              fileList={fileList}
              onChange={({ fileList }) => setFileList(fileList)}
              showUploadList={false}
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              disabled={uploading}
            >
              <Button icon={<UploadOutlined />} loading={uploading}>
                上传检查报告（PDF/图片，最大20MB）
              </Button>
            </Upload>

            {reports.length > 0 && (
              <List
                style={{ marginTop: 12 }}
                size="small"
                bordered
                dataSource={reports}
                renderItem={(report) => (
                  <List.Item
                    actions={[
                      report.fileUrl ? (
                        <a href={report.fileUrl} target="_blank" rel="noopener noreferrer">查看</a>
                      ) : null,
                      <Popconfirm
                        title="确定删除此报告？"
                        onConfirm={() => handleDeleteReport(report.id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <DeleteOutlined style={{ color: '#ff4d4f' }} />
                      </Popconfirm>,
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      avatar={getFileIcon(report.fileType)}
                      title={report.title}
                      description={`${report.fileName} · ${formatFileSize(report.fileSize)}`}
                    />
                  </List.Item>
                )}
              />
            )}
          </div>

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

          <Divider />

          <ProFormDigit
            name="totalFee"
            label="费用"
            placeholder="请输入费用金额"
            fieldProps={{ 
              prefix: '¥',
              precision: 2,
              min: 0,
            }}
            width="sm"
          />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default MedicalRecordFormPage;
