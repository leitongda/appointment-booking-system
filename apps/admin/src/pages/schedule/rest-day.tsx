import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Tag, Popconfirm, Alert } from 'antd';
import { useRef } from 'react';
import { history } from '@umijs/max';
import { restDayApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { RestDay } from '@hospital/api';

const RestDayPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await restDayApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await restDayApi.cancel(id);
      message.success('取消成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '取消失败');
    }
  };

  const columns: ProColumns<RestDay>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 150,
    },
    {
      title: '休息医生',
      dataIndex: 'doctorNames',
      width: 200,
      search: false,
      render: (_, record) => {
        if (!record.doctorNames || record.doctorNames.length === 0) {
          return <Tag color="red">全部医生</Tag>;
        }
        return (
          <span>
            {record.doctorNames.map((name, index) => (
              <Tag key={index} color="blue">{name}</Tag>
            ))}
          </span>
        );
      },
    },
    {
      title: '休息原因',
      dataIndex: 'reason',
      width: 200,
      ellipsis: true,
      search: false,
    },
    {
      title: '开始日期',
      dataIndex: 'startDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '结束日期',
      dataIndex: 'endDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '生效中', status: 'Success' },
        0: { text: '已取消', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => [
        record.status === 1 && (
          <Popconfirm 
            key="cancel"
            title="确定取消该休息日设置吗？" 
            onConfirm={() => handleCancel(record.id)}
          >
            <a>取消</a>
          </Popconfirm>
        ),
        <Popconfirm 
          key="delete"
          title="确定删除该记录吗？" 
          onConfirm={() => handleDelete(record.id)}
        >
          <a style={{ color: '#ff4d4f' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <Alert
        message="排班权重说明"
        description="停诊 > 自定义排班 > 休息日设置 > 普通排班"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <ProTable<RestDay>
        headerTitle="休息日设置"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await restDayApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/schedule/rest-day/create')}
          >
            添加
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default RestDayPage;
