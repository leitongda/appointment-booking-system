import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space } from 'antd';
import { useRef } from 'react';
import { history } from '@umijs/max';
import { doctorBookingSettingApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { DoctorBookingSetting } from '@hospital/shared';

const DoctorBookingSettingPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await doctorBookingSettingApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<DoctorBookingSetting>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 150,
      ellipsis: true,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 120,
    },
    {
      title: '预约开始日期',
      dataIndex: 'bookingStartOffset',
      width: 120,
      search: false,
      render: (_, record) => {
        const offset = record.bookingStartOffset;
        if (offset === 0) return '当天';
        if (offset === 1) return '第2天';
        return `第${offset + 1}天`;
      },
    },
    {
      title: '预约范围',
      dataIndex: 'bookingRangeDays',
      width: 100,
      search: false,
      render: (val) => `${val}天`,
    },
    {
      title: '放号时间',
      dataIndex: 'releaseTime',
      width: 100,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
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
      render: (_, record) => (
        <Space>
          <a onClick={() => history.push(`/doctor/booking-setting/${record.id}/edit`)}>编辑</a>
          <Popconfirm
            title="确定删除该设置吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<DoctorBookingSetting>
        headerTitle="医生预约设置"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(
            await doctorBookingSettingApi.getList({
              ...rest,
              page: current,
              pageSize,
            })
          );
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/doctor/booking-setting/create')}
          >
            添加医生预约管理
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default DoctorBookingSettingPage;
