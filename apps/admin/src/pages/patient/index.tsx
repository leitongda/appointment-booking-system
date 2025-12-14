import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Popconfirm, Space, Tag } from 'antd';
import { useRef } from 'react';
import { history } from '@umijs/max';
import { patientApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { PatientListItem } from '@hospital/api';

const SOURCE_MAP: Record<number, string> = {
  1: '用户添加',
  2: '管理员添加',
};

const PatientPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();

  const handleBlacklist = async (id: string, add: boolean) => {
    try {
      if (add) {
        await patientApi.addToBlacklist(id, '多次爽约');
        message.success('已加入黑名单');
      } else {
        await patientApi.removeFromBlacklist(id);
        message.success('已移出黑名单');
      }
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<PatientListItem>[] = [
    { title: '就诊卡编号', dataIndex: 'cardNo', width: 140, ellipsis: true },
    { title: '姓名', dataIndex: 'name', width: 80 },
    { title: '手机号', dataIndex: 'phone', width: 120 },
    { title: '身份证号', dataIndex: 'idCard', width: 180, search: false, ellipsis: true },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 60,
      search: false,
      render: (val) => (val === 1 ? '男' : val === 2 ? '女' : '-'),
    },
    { title: '与本人关系', dataIndex: 'relationship', width: 100, search: false },
    {
      title: '来源',
      dataIndex: 'source',
      width: 100,
      search: false,
      render: (_, record) => SOURCE_MAP[record.source || 1] || '-',
    },
    { title: '预约次数', dataIndex: 'appointmentCount', width: 90, search: false },
    { title: '爽约次数', dataIndex: 'noShowCount', width: 90, search: false },
    {
      title: '黑名单',
      dataIndex: 'isBlacklist',
      width: 80,
      valueEnum: { true: { text: '是', status: 'Error' }, false: { text: '否', status: 'Default' } },
      render: (_, record) => record.isBlacklist ? <Tag color="red">黑名单</Tag> : '-',
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 140,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <a onClick={() => history.push(`/patient/${record.id}`)}>详情</a>
          {record.isBlacklist ? (
            <Popconfirm title="确定移出黑名单吗？" onConfirm={() => handleBlacklist(record.id, false)}>
              <a>移出黑名单</a>
            </Popconfirm>
          ) : (
            <Popconfirm title="确定加入黑名单吗？" onConfirm={() => handleBlacklist(record.id, true)}>
              <a style={{ color: '#ff4d4f' }}>加黑名单</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<PatientListItem>
        headerTitle="患者列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1300 }}
        request={async (params) => {
          const { current, pageSize, name, phone, cardNo, ...rest } = params;
          const keyword = name || phone || cardNo;
          return toProTableResult(await patientApi.getList({ ...rest, keyword, page: current, pageSize }));
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default PatientPage;
