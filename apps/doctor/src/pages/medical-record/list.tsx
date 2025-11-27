import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';

interface MedicalRecord {
  id: string;
  patientName: string;
  diagnosis: string;
  visitDate: string;
}

const MedicalRecordListPage: React.FC = () => {
  const columns: ProColumns<MedicalRecord>[] = [
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    { title: '诊断', dataIndex: 'diagnosis', width: 200, ellipsis: true },
    { title: '就诊日期', dataIndex: 'visitDate', width: 120, valueType: 'date' },
    { title: '操作', width: 100, render: () => <a>查看</a> },
  ];

  return (
    <PageContainer>
      <ProTable<MedicalRecord>
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default MedicalRecordListPage;

