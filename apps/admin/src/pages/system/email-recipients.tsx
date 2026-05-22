import type { ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormCheckbox,
} from '@ant-design/pro-components';
import { Tag, Switch, Space } from 'antd';
import { useState, useEffect } from 'react';
import { storeEmailRecipientApi, storeApi } from '@hospital/api';
import type { StoreEmailRecipient, EventTypeOption } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationButton, OperationGroup } from '@/components/ListOperations';
import { emailRules } from '@/utils/formValidators';

const StoreEmailRecipientsPage: React.FC = () => {
  const { actionRef, message, handleDelete, reload } = useListPage({
    deleteFn: storeEmailRecipientApi.delete,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<StoreEmailRecipient | null>(null);
  const [eventTypeOptions, setEventTypeOptions] = useState<EventTypeOption[]>([]);
  const [storeOptions, setStoreOptions] = useState<{ label: string; value: string }[]>([]);

  // 加载事件类型选项和门店列表
  useEffect(() => {
    storeEmailRecipientApi.getEventTypes().then(setEventTypeOptions).catch(() => {
      message.warning('加载事件类型失败');
    });
    storeApi.getAll?.().then((stores: any[]) => {
      setStoreOptions(
        stores.map((s: any) => ({ label: s.name, value: s.id })),
      );
    }).catch(() => {
      // fallback: 通过列表接口获取
      storeApi.getList({ pageSize: 100 }).then((res: any) => {
        const list = res.data || res.items || res || [];
        setStoreOptions(
          list.map((s: any) => ({ label: s.name, value: s.id })),
        );
      }).catch(() => {
        message.warning('加载门店列表失败');
      });
    });
  }, []);

  // 事件类型 label 映射
  const eventTypeLabelMap = eventTypeOptions.reduce<Record<string, string>>(
    (acc, item) => {
      acc[item.value] = item.label;
      return acc;
    },
    {},
  );

  const handleStatusChange = async (id: string, status: boolean) => {
    try {
      await storeEmailRecipientApi.update(id, { status: status ? 1 : 0 });
      message.success('状态更新成功');
      reload();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingRecord) {
        await storeEmailRecipientApi.update(editingRecord.id, {
          name: values.name,
          email: values.email,
          eventTypes: values.eventTypes || [],
          status: values.status,
        });
        message.success('更新成功');
      } else {
        await storeEmailRecipientApi.create({
          storeId: values.storeId,
          name: values.name,
          email: values.email,
          eventTypes: values.eventTypes || [],
          status: values.status ?? 1,
        });
        message.success('创建成功');
      }
      setModalVisible(false);
      setEditingRecord(null);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const columns: ProColumns<StoreEmailRecipient>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 150,
      ellipsis: true,
      search: false,
    },
    {
      title: '门店',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        options: storeOptions,
        placeholder: '请选择门店',
      },
    },
    {
      title: '接收人',
      dataIndex: 'name',
      width: 120,
      ellipsis: true,
      search: false,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      width: 200,
      ellipsis: true,
      search: false,
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '姓名/邮箱',
      },
    },
    {
      title: '订阅事件',
      dataIndex: 'eventTypes',
      width: 300,
      search: false,
      render: (_, record) => (
        <Space size={[0, 4]} wrap>
          {(record.eventTypes || []).map((et) => (
            <Tag key={et} color="blue">
              {eventTypeLabelMap[et] || et}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
      render: (_, record) => (
        <Switch
          checked={record.status === 1}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleStatusChange(record.id, checked)}
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="custom"
            label="编辑"
            onClick={() => {
              setEditingRecord(record);
              setModalVisible(true);
            }}
          />
          <OperationButton
            type="delete"
            confirmText="确定删除该接收人吗？"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<StoreEmailRecipient>
        headerTitle="门店邮件接收人"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={createListRequest(storeEmailRecipientApi.getList, (params) => {
          const { keyword, storeId, status, ...rest } = params;
          return {
            ...rest,
            keyword: keyword || undefined,
            storeId: storeId || undefined,
            status: status !== undefined && status !== '' ? Number(status) : undefined,
          };
        })}
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          <CreateButton
            key="add"
            label="新增接收人"
            onClick={() => {
              setEditingRecord(null);
              setModalVisible(true);
            }}
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑邮件接收人' : '新增邮件接收人'}
        open={modalVisible}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) setEditingRecord(null);
        }}
        onFinish={handleSubmit}
        initialValues={
          editingRecord
            ? {
                storeId: editingRecord.storeId,
                name: editingRecord.name,
                email: editingRecord.email,
                eventTypes: editingRecord.eventTypes || [],
                status: editingRecord.status,
              }
            : { status: 1, eventTypes: [] }
        }
        modalProps={{ destroyOnHidden: true }}
        width={520}
      >
        <ProFormSelect
          name="storeId"
          label="门店"
          options={storeOptions}
          placeholder="请选择门店"
          rules={[{ required: true, message: '请选择门店' }]}
          disabled={!!editingRecord}
        />
        <ProFormText
          name="name"
          label="接收人姓名"
          placeholder="请输入接收人姓名"
          rules={[{ required: true, message: '请输入接收人姓名' }]}
        />
        <ProFormText
          name="email"
          label="邮箱地址"
          placeholder="请输入邮箱地址"
          rules={[
            { required: true, message: '请输入邮箱地址' },
            emailRules,
          ]}
        />
        <ProFormCheckbox.Group
          name="eventTypes"
          label="订阅事件"
          options={eventTypeOptions.map((o) => ({
            label: o.label,
            value: o.value,
          }))}
          rules={[{ required: true, message: '请至少选择一个事件类型' }]}
        />
        <ProFormSelect
          name="status"
          label="状态"
          options={[
            { label: '启用', value: 1 },
            { label: '禁用', value: 0 },
          ]}
          rules={[{ required: true, message: '请选择状态' }]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default StoreEmailRecipientsPage;
