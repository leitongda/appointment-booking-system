import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Modal, Descriptions, Divider } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';

interface MedicalRecord {
  id: string;
  appointmentNo: string;
  patientName: string;
  patientPhone: string;
  diagnosis: string;
  visitDate: string;
  chiefComplaint: string;
  treatment: string;
  prescription: string;
  advice: string;
  createdAt: string;
}

const MedicalRecordListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<MedicalRecord | null>(null);

  const handleView = (record: MedicalRecord) => {
    setCurrentRecord(record);
    setDetailVisible(true);
  };

  const columns: ProColumns<MedicalRecord>[] = [
    { title: '就诊日期', dataIndex: 'visitDate', width: 120, valueType: 'date' },
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    { title: '手机号', dataIndex: 'patientPhone', width: 130, search: false },
    { title: '主诉', dataIndex: 'chiefComplaint', width: 200, ellipsis: true, search: false },
    { title: '诊断', dataIndex: 'diagnosis', width: 200, ellipsis: true },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option',
      width: 80,
      render: (_, record) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => handleView(record)}>
          查看
        </Button>
      )
    },
  ];

  // Mock 数据
  const mockData: MedicalRecord[] = [
    {
      id: '1',
      appointmentNo: 'YY20241127001',
      patientName: '张三',
      patientPhone: '13800138000',
      diagnosis: '高血压',
      visitDate: '2024-11-27',
      chiefComplaint: '头晕、乏力3天',
      treatment: '药物治疗，控制血压',
      prescription: '1. 降压药 每日2次，每次1片\n2. 维生素B 每日1次，每次2片',
      advice: '注意休息，低盐低脂饮食，定期复查',
      createdAt: '2024-11-27 10:30:00',
    },
  ];

  return (
    <PageContainer>
      <ProTable<MedicalRecord>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          // TODO: 调用真实 API
          return { data: mockData, success: true, total: mockData.length };
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
              <Descriptions.Item label="患者姓名">{currentRecord.patientName}</Descriptions.Item>
              <Descriptions.Item label="手机号">{currentRecord.patientPhone}</Descriptions.Item>
              <Descriptions.Item label="就诊日期">{currentRecord.visitDate}</Descriptions.Item>
              <Descriptions.Item label="预约单号">{currentRecord.appointmentNo}</Descriptions.Item>
            </Descriptions>
            
            <Divider orientation="left">病情记录</Divider>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="主诉">{currentRecord.chiefComplaint}</Descriptions.Item>
              <Descriptions.Item label="诊断">
                <Tag color="blue">{currentRecord.diagnosis}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="治疗方案">{currentRecord.treatment}</Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">处方与医嘱</Divider>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="处方">
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{currentRecord.prescription}</pre>
              </Descriptions.Item>
              <Descriptions.Item label="医嘱">{currentRecord.advice}</Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default MedicalRecordListPage;
