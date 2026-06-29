import { PlusOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormTextArea,
} from '@ant-design/pro-components';
import { Tag, Popconfirm, Button, Space } from 'antd';
import { useState, useCallback } from 'react';
import { history } from '@umijs/max';
import { dictApi } from '@hospital/api';
import type { DictTypeItem, DictTypeCreateData, DictTypeUpdateData } from '@hospital/api';
import { useListPage } from '@/hooks/useListPage';
import { createListRequest } from '@/utils/proTable';

const DictTypeListPage: React.FC = () => {
  const { actionRef, message } = useListPage();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DictTypeItem | null>(null);

  const handleCreate = useCallback(() => {
    setEditingRecord(null);
    setModalOpen(true);
  }, []);

  const handleEdit = useCallback((record: DictTypeItem) => {
    setEditingRecord(record);
    setModalOpen(true);
  }, []);

  const handleToggleStatus = useCallback(
    async (record: DictTypeItem) => {
      try {
        await dictApi.updateType(record.id, { status: record.status === 1 ? 0 : 1 });
        message.success('更新成功');
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '更新失败');
      }
    },
    [message]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await dictApi.deleteType(id);
        message.success('删除成功');
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '删除失败');
      }
    },
    [message]
  );

  const handleModalFinish = useCallback(
    async (values: DictTypeCreateData | DictTypeUpdateData) => {
      try {
        if (editingRecord) {
          await dictApi.updateType(editingRecord.id, values as DictTypeUpdateData);
          message.success('更新成功');
        } else {
          await dictApi.createType(values as DictTypeCreateData);
          message.success('创建成功');
        }
        setModalOpen(false);
        actionRef.current?.reload();
        return true;
      } catch (error: any) {
        message.error(error.message || '操作失败');
        return false;
      }
    },
    [editingRecord, message]
  );

  const columns: ProColumns<DictTypeItem>[] = [
    {
      title: '字典编码',
      dataIndex: 'code',
      width: 180,
      fixed: 'left',
    },
    {
      title: '字典名称',
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
      dataIndex: 'status',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.status === 1 ? 'success' : 'default'}>
          {record.status === 1 ? '启用' : '禁用'}
        </Tag>
      ),
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
      width: 240,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <a onClick={() => handleEdit(record)}>编辑</a>
          <a onClick={() => history.push(`/system/dictionaries/${record.id}/items`)}>
            字典项
          </a>
          <a onClick={() => handleToggleStatus(record)}>
            {record.status === 1 ? '禁用' : '启用'}
          </a>
          <Popconfirm
            title="确定删除该字典类型吗？"
            description="删除后该类型下的所有字典项也会被禁用"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      title="字典管理"
      content="管理系统中的数据字典，用于统一管理下拉选项、枚举值等配置数据"
    >
      <ProTable<DictTypeItem>
        headerTitle="字典类型列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(dictApi.getTypeList)}
        search={{ labelWidth: 'auto' }}
        options={{ density: false, fullScreen: false, reload: true, setting: true }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        scroll={{ x: 1200 }}
        rowClassName={(record) => (record.status === 0 ? 'disabled-row' : '')}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新增字典类型
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑字典类型' : '新增字典类型'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleModalFinish}
        width={520}
        modalProps={{ destroyOnHidden: true }}
        initialValues={editingRecord ? {
          code: editingRecord.code,
          name: editingRecord.name,
          description: editingRecord.description,
        } : undefined}
      >
        <ProFormText
          name="code"
          label="字典编码"
          placeholder="请输入字典编码，如 doctor_title"
          rules={[
            { required: true, message: '请输入字典编码' },
            { pattern: /^[a-z][a-z0-9_]*$/, message: '编码只能包含小写字母、数字和下划线，且以字母开头' },
          ]}
          disabled={!!editingRecord}
          tooltip="编码创建后不可修改，用于系统识别"
        />
        <ProFormText
          name="name"
          label="字典名称"
          placeholder="请输入字典名称"
          rules={[{ required: true, message: '请输入字典名称' }]}
        />
        <ProFormTextArea
          name="description"
          label="描述"
          placeholder="请输入字典类型描述"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default DictTypeListPage;
