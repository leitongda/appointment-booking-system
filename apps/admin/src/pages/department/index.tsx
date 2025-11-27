import { PlusOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Modal, Space, Tag } from 'antd';
import { useRef, useState } from 'react';
import type { Department } from '@hospital/shared';
import { STATUS_MAP } from '@hospital/shared';

const DepartmentPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);

  const columns: ProColumns<Department>[] = [
    {
      title: '科室名称',
      dataIndex: 'name',
      width: 200,
    },
    {
      title: '科室编码',
      dataIndex: 'code',
      width: 120,
      search: false,
    },
    {
      title: '上级科室',
      dataIndex: ['parent', 'name'],
      width: 150,
      search: false,
    },
    {
      title: '是否热门',
      dataIndex: 'isHot',
      width: 100,
      search: false,
      render: (_, record) => (
        record.isHot ? <Tag color="red">热门</Tag> : <Tag>普通</Tag>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        0: { text: '禁用', status: 'Default' },
        1: { text: '启用', status: 'Success' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 180,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => (
        <Space>
          <a onClick={() => message.info('编辑')}>编辑</a>
          <a onClick={() => message.info('删除')}>删除</a>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Department>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
          >
            新增科室
          </Button>,
        ]}
        request={async (params) => {
          // TODO: 调用 API 获取数据
          return {
            data: [],
            success: true,
            total: 0,
          };
        }}
      />
    </PageContainer>
  );
};

export default DepartmentPage;

