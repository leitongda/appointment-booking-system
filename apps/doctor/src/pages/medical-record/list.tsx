import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Modal, Descriptions, Divider, message } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { medicalRecordApi } from '@hospital/api';
import type { MedicalRecordListItem, MedicalRecord } from '@hospital/api';

const MedicalRecordListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<MedicalRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleView = async (record: MedicalRecordListItem) => {
    setDetailLoading(true);
    try {
      const detail = await medicalRecordApi.getDetail(record.id);
      setCurrentRecord(detail);
      setDetailVisible(true);
    } catch (error: any) {
      message.error(error.message || '获取病历详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ProColumns<MedicalRecordListItem>[] = [
    { title: '病历号', dataIndex: 'recordNo', width: 160 },
    { 
      title: '就诊日期', 
      dataIndex: 'visitDate', 
      width: 120, 
      valueType: 'date',
      search: {
        transform: (value) => ({ startDate: value }),
      }
    },
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    { title: '科室', dataIndex: 'departmentName', width: 100, search: false },
    { title: '诊断', dataIndex: 'diagnosis', width: 200, ellipsis: true },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 80,
      valueEnum: {
        1: { text: '草稿', status: 'Default' },
        2: { text: '已完成', status: 'Success' },
      },
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option',
      width: 80,
      render: (_, record) => (
        <Button 
          type="link" 
          icon={<EyeOutlined />} 
          loading={detailLoading}
          onClick={() => handleView(record)}
        >
          查看
        </Button>
      )
    },
  ];

  return (
    <PageContainer>
      <ProTable<MedicalRecordListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            const { current, pageSize, keyword, ...rest } = params;
            const result = await medicalRecordApi.getMyRecords({
              page: current || 1,
              pageSize: pageSize || 10,
              ...rest,
            });
            return { 
              data: result.data, 
              success: true, 
              total: result.total 
            };
          } catch (error: any) {
            message.error(error.message || '获取病历列表失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

      <Modal
        title="病历详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {currentRecord && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="病历号">{currentRecord.recordNo}</Descriptions.Item>
              <Descriptions.Item label="就诊日期">
                {currentRecord.visitDate?.substring(0, 10)}
              </Descriptions.Item>
              <Descriptions.Item label="患者姓名">{currentRecord.patientName}</Descriptions.Item>
              <Descriptions.Item label="手机号">
                {currentRecord.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
              </Descriptions.Item>
              <Descriptions.Item label="科室">{currentRecord.departmentName}</Descriptions.Item>
              <Descriptions.Item label="医生">{currentRecord.doctorName}</Descriptions.Item>
            </Descriptions>
            
            <Divider orientation="left">病情记录</Divider>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="主诉">{currentRecord.chiefComplaint || '-'}</Descriptions.Item>
              <Descriptions.Item label="现病史">{currentRecord.presentIllness || '-'}</Descriptions.Item>
              <Descriptions.Item label="既往史">{currentRecord.pastHistory || '-'}</Descriptions.Item>
              <Descriptions.Item label="过敏史">{currentRecord.allergyHistory || '-'}</Descriptions.Item>
              <Descriptions.Item label="体格检查">{currentRecord.physicalExam || '-'}</Descriptions.Item>
              <Descriptions.Item label="辅助检查">{currentRecord.auxiliaryExam || '-'}</Descriptions.Item>
              <Descriptions.Item label="诊断">
                <Tag color="blue">{currentRecord.diagnosis}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="治疗方案">{currentRecord.treatment || '-'}</Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">处方与医嘱</Divider>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="处方">
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {currentRecord.prescription || '-'}
                </pre>
              </Descriptions.Item>
              <Descriptions.Item label="医嘱">{currentRecord.advice || '-'}</Descriptions.Item>
              {currentRecord.totalFee !== undefined && currentRecord.totalFee > 0 && (
                <Descriptions.Item label="费用">
                  <span style={{ color: '#f50', fontWeight: 500 }}>
                    ¥{currentRecord.totalFee.toFixed(2)}
                  </span>
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default MedicalRecordListPage;
