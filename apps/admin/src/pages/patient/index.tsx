import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag, Space } from 'antd';
import { GENDER_MAP } from '@hospital/shared';

interface PatientRecord {
  id: string;
  name: string;
  phone: string;
  gender: number;
  idCard: string;
  appointmentCount: number;
  noShowCount: number;
  isBlacklist: boolean;
  createdAt: string;
}

const PatientPage: React.FC = () => {
  const columns: ProColumns<PatientRecord>[] = [
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    { title: '性别', dataIndex: 'gender', width: 80, render: (_, r) => GENDER_MAP[r.gender] },
    { title: '身份证', dataIndex: 'idCard', width: 180, search: false },
    { title: '预约次数', dataIndex: 'appointmentCount', width: 100, search: false },
    { title: '爽约次数', dataIndex: 'noShowCount', width: 100, search: false },
    { title: '黑名单', dataIndex: 'isBlacklist', width: 80, render: (_, r) => r.isBlacklist ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
    { title: '注册时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { title: '操作', valueType: 'option', width: 150, render: (_, r) => (
      <Space>
        <a>查看</a>
        {r.isBlacklist ? <a>移出黑名单</a> : <a style={{ color: 'red' }}>加入黑名单</a>}
      </Space>
    )},
  ];

  return (
    <PageContainer>
      <ProTable<PatientRecord>
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default PatientPage;

