import { PlusOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormDigit,
  ProFormTextArea,
} from '@ant-design/pro-components';
import { Tag, Popconfirm, Button, Space, Card, Descriptions } from 'antd';
import { useState, useCallback, useEffect } from 'react';
import { useParams, history } from '@umijs/max';
import { dictApi } from '@hospital/api';
import type { DictTypeItem, DictItemData, DictItemCreateData, DictItemUpdateData } from '@hospital/api';
import { useListPage } from '@/hooks/useListPage';
import { createListRequest } from '@/utils/proTable';
import { clearDictCache } from '@/hooks/useDict';

const DictItemsPage: React.FC = () => {
  const { typeId } = useParams();
  const { actionRef, message } = useListPage();
  const [dictType, setDictType] = useState<DictTypeItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DictItemData | null>(null);

  useEffect(() => {
    if (typeId) {
      dictApi.getTypeDetail(typeId).then(setDictType).catch(() => {
        message.error('加载字典类型信息失败');
      });
    }
  }, [typeId, message]);

  // 操作成功后清除该字典类型的缓存
  const refreshCache = useCallback(() => {
    if (dictType?.code) {
      clearDictCache(dictType.code);
    }
  }, [dictType]);

  const handleCreate = useCallback(() => {
    setEditingRecord(null);
    setModalOpen(true);
  }, []);

  const handleEdit = useCallback((record: DictItemData) => {
    setEditingRecord(record);
    setModalOpen(true);
  }, []);

  const handleToggleStatus = useCallback(
    async (record: DictItemData) => {
      if (!typeId) return;
      try {
        await dictApi.updateItem(typeId, record.id, {
          status: record.status === 1 ? 0 : 1,
        });
        message.success('更新成功');
        refreshCache();
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '更新失败');
      }
    },
    [typeId, message, refreshCache]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      if (!typeId) return;
      try {
        await dictApi.deleteItem(typeId, id);
        message.success('删除成功');
        refreshCache();
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '删除失败');
      }
    },
    [typeId, message, refreshCache]
  );

  const handleModalFinish = useCallback(
    async (values: DictItemCreateData | DictItemUpdateData) => {
      if (!typeId) return false;
      try {
        if (editingRecord) {
          await dictApi.updateItem(typeId, editingRecord.id, values as DictItemUpdateData);
          message.success('更新成功');
        } else {
          await dictApi.createItem(typeId, values as DictItemCreateData);
          message.success('创建成功');
        }
        setModalOpen(false);
        refreshCache();
        actionRef.current?.reload();
        return true;
      } catch (error: any) {
        message.error(error.message || '操作失败');
        return false;
      }
    },
    [typeId, editingRecord, message, refreshCache]
  );

  const columns: ProColumns<DictItemData>[] = [
    {
      title: '标签',
      dataIndex: 'label',
      width: 200,
    },
    {
      title: '值',
      dataIndex: 'value',
      width: 150,
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
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.status === 1 ? 'success' : 'default'}>
          {record.status === 1 ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '扩展数据',
      dataIndex: 'extra',
      width: 200,
      ellipsis: true,
      search: false,
      render: (_, record) => {
        if (!record.extra) return '-';
        const str = JSON.stringify(record.extra);
        return str.length > 50 ? str.slice(0, 50) + '...' : str;
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
      width: 160,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <a onClick={() => handleEdit(record)}>编辑</a>
          <a onClick={() => handleToggleStatus(record)}>
            {record.status === 1 ? '禁用' : '启用'}
          </a>
          <Popconfirm
            title="确定删除该字典项吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (!typeId) return null;

  return (
    <PageContainer
      title={dictType ? `字典项管理 - ${dictType.name}` : '字典项管理'}
      content="管理字典类型下的具体选项数据"
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => history.push('/system/dictionaries')}>
          返回字典列表
        </Button>
      }
    >
      {dictType && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="字典编码">{dictType.code}</Descriptions.Item>
            <Descriptions.Item label="字典名称">{dictType.name}</Descriptions.Item>
            <Descriptions.Item label="描述">{dictType.description || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <ProTable<DictItemData>
        headerTitle="字典项列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest((params) => dictApi.getItems(typeId, params))}
        search={false}
        options={{ density: false, fullScreen: false, reload: true, setting: true }}
        pagination={{ defaultPageSize: 50, showSizeChanger: true }}
        rowClassName={(record) => (record.status === 0 ? 'disabled-row' : '')}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新增字典项
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑字典项' : '新增字典项'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleModalFinish}
        width={520}
        modalProps={{ destroyOnHidden: true }}
        initialValues={editingRecord ? {
          label: editingRecord.label,
          value: editingRecord.value,
          sortOrder: editingRecord.sortOrder,
          extra: editingRecord.extra ? JSON.stringify(editingRecord.extra, null, 2) : '',
        } : { sortOrder: 0 }}
      >
        <ProFormText
          name="label"
          label="显示标签"
          placeholder="请输入显示标签，如：主任医师"
          rules={[{ required: true, message: '请输入显示标签' }]}
        />
        <ProFormText
          name="value"
          label="字典值"
          placeholder="请输入字典值"
          rules={[{ required: true, message: '请输入字典值' }]}
          tooltip="字典值在同一字典类型下必须唯一"
        />
        <ProFormDigit
          name="sortOrder"
          label="排序"
          placeholder="数字越小越靠前"
          min={0}
          max={9999}
          fieldProps={{ precision: 0 }}
        />
        <ProFormTextArea
          name="extra"
          label="扩展数据"
          placeholder='JSON 格式，如：{"color": "red", "icon": "star"}'
          fieldProps={{
            autoSize: { minRows: 2, maxRows: 6 },
          }}
          rules={[
            {
              validator: async (_: any, value: string) => {
                if (!value) return;
                try {
                  JSON.parse(value);
                } catch {
                  throw new Error('请输入合法的 JSON 格式');
                }
              },
            },
          ]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default DictItemsPage;
