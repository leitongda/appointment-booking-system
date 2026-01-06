import { PageContainer, ProTable, ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Space, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useState, useRef } from 'react';
import { history } from '@umijs/max';
import { shiftTypeApi } from '@hospital/api';
import type { ShiftType } from '@hospital/shared';

/**
 * 班次类型管理页面
 */
const ShiftTypeListPage: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleDelete = async (id: string) => {
    try {
      setLoading(true);
      await shiftTypeApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (record: ShiftType) => {
    try {
      setLoading(true);
      await shiftTypeApi.update(record.id, {
        enabled: !record.enabled,
      });
      message.success('更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  const actionRef = useRef<ActionType>();

  const columns: ProColumns<ShiftType>[] = [
    {
      title: '类型代码',
      dataIndex: 'code',
      width: 150,
      fixed: 'left',
    },
    {
      title: '类型名称',
      dataIndex: 'name',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      width: 300,
      ellipsis: true,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 100,
      search: false,
      render: (_, record) => (
        <Tag color={record.enabled ? 'success' : 'default'}>
          {record.enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 180,
      search: false,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => history.push(`/system/shift-types/${record.id}/edit`)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => handleToggleStatus(record)}
          >
            {record.enabled ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，确定要删除吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      title="班次类型管理"
      content="管理系统中的班次类型，用于规则管理和排班管理"
    >
      <ProTable<ShiftType>
        actionRef={actionRef}
        rowKey="id"
        loading={loading}
        columns={columns}
        request={async (params) => {
          const { current, pageSize, code, name, enabled } = params;

          try {
            const result = await shiftTypeApi.getList({
              page: current,
              pageSize: pageSize,
              keyword: code || name,
              enabled,
            });

            // 后端返回 PageResult 格式: { data, total }
            const data = result.data || [];

            return {
              data: data,
              success: true,
              total: result.total || 0,
            };
          } catch (error: any) {
            message.error(error.message || '加载数据失败');
            return {
              data: [],
              success: false,
              total: 0,
            };
          }
        }}
        columnsState={{
          persistenceKey: 'shift-type-list-table',
          persistenceType: 'localStorage',
        }}
        rowClassName={(record) => (!record.enabled ? 'disabled-row' : '')}
        search={{
          labelWidth: 'auto',
        }}
        options={{
          density: false,
          fullScreen: false,
          reload: true,
          setting: true,
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        dateFormatter="string"
        headerTitle="班次类型列表"
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/system/shift-types/create')}
          >
            新增班次类型
          </Button>,
        ]}
      />
    </PageContainer>
  );
};

export default ShiftTypeListPage;
