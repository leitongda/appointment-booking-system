import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Avatar, Switch } from 'antd';
import { PlusOutlined, UserOutlined } from '@ant-design/icons';
import { useRef } from 'react';
import { history } from 'umi';
import { doctorApi } from '@hospital/api';
import { DOCTOR_TITLE_MAP } from '@hospital/shared';
import type { Doctor } from '@hospital/shared';

const DoctorListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await doctorApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleStatusChange = async (id: string, status: number) => {
    try {
      await doctorApi.update(id, { status });
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<Doctor>[] = [
    { 
      title: '医生', 
      dataIndex: 'name', 
      width: 180,
      render: (_, r) => (
        <Space>
          <Avatar src={r.avatar} icon={<UserOutlined />} />
          <span>{r.name}</span>
        </Space>
      )
    },
    { 
      title: '职称', 
      dataIndex: 'title', 
      width: 100,
      valueEnum: DOCTOR_TITLE_MAP
    },
    { title: '所属科室', dataIndex: 'departmentName', width: 120 },
    { title: '手机号', dataIndex: 'phone', width: 130, search: false },
    { 
      title: '挂号费', 
      dataIndex: 'registrationFee', 
      width: 100, 
      search: false,
      render: (_, r) => `¥${r.registrationFee}`
    },
    { 
      title: '推荐', 
      dataIndex: 'isRecommended', 
      width: 80,
      search: false,
      render: (_, r) => r.isRecommended ? <Tag color="red">是</Tag> : <Tag>否</Tag>
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      valueEnum: { 0: { text: '禁用' }, 1: { text: '启用' } },
      render: (_, r) => (
        <Switch 
          checked={r.status === 1} 
          onChange={(checked) => handleStatusChange(r.id, checked ? 1 : 0)}
          checkedChildren="启用" 
          unCheckedChildren="禁用"
        />
      )
    },
    { 
      title: '操作', 
      valueType: 'option',
      width: 180,
      render: (_, record) => (
        <Space>
          <a onClick={() => history.push(`/doctor/detail/${record.id}`)}>查看</a>
          <a onClick={() => history.push(`/doctor/edit/${record.id}`)}>编辑</a>
          <Popconfirm title="确定删除该医生吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      )
    },
  ];

  return (
    <PageContainer>
      <ProTable<Doctor>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => history.push('/doctor/add')}>
            新增医生
          </Button>
        ]}
        request={async (params) => {
          const { current, pageSize, name, status } = params;
          const result = await doctorApi.getList({ name, status, page: current, pageSize });
          return { data: result.data, success: true, total: result.total };
        }}
      />
    </PageContainer>
  );
};

export default DoctorListPage;
