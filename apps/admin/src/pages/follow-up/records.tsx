import { EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormTextArea,
  ProFormSelect,
  ProFormDatePicker,
} from '@ant-design/pro-components';
import { App, Drawer, Descriptions, Popconfirm, Space, Spin, Tag } from 'antd';
import { useRef, useState, useCallback } from 'react';
import { departmentApi, doctorApi, followUpApi } from '@hospital/api';
import type { FollowUpRecord, FollowUpRecordListItem } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import dayjs from 'dayjs';

const CONDITION_MAP: Record<string, { text: string; color: string }> = {
  improved: { text: '好转', color: 'success' },
  stable: { text: '稳定', color: 'processing' },
  worsened: { text: '恶化', color: 'error' },
};

const FollowUpRecordsPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<FollowUpRecord | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<FollowUpRecord | null>(null);

  const handleView = async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await followUpApi.getRecordDetail(id);
      setCurrentRecord(result);
    } catch (error: any) {
      message.error(error.message || '加载详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleEdit = async (id: string) => {
    try {
      const result = await followUpApi.getRecordDetail(id);
      setEditingRecord(result);
      setEditModalOpen(true);
    } catch (error: any) {
      message.error(error.message || '加载详情失败');
    }
  };

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await followUpApi.deleteRecord(id);
        message.success('删除成功');
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '删除失败');
      }
    },
    [message],
  );

  const columns: ProColumns<FollowUpRecordListItem>[] = [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '患者姓名/随访内容' },
    },
    {
      title: '医生',
      dataIndex: 'doctorId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: { showSearch: true, optionFilterProp: 'label', placeholder: '请选择医生' },
      request: async () => {
        try {
          const docs = await fetchAllData((p, ps) => doctorApi.getList({ page: p, pageSize: ps }));
          return [{ label: '全部医生', value: '' }, ...docs.map((d: any) => ({ label: d.name, value: d.id }))];
        } catch {
          return [];
        }
      },
    },
    {
      title: '日期范围',
      dataIndex: 'dateRange',
      hideInTable: true,
      valueType: 'dateRange',
      search: {
        transform: (value) => {
          if (!value) return {};
          return { startDate: value[0], endDate: value[1] };
        },
      },
    },
    { title: '患者', dataIndex: 'patientName', width: 100, search: false },
    { title: '医生', dataIndex: 'doctorName', width: 100, search: false },
    {
      title: '随访日期',
      dataIndex: 'followUpDate',
      width: 120,
      valueType: 'date',
      search: false,
    },
    { title: '随访内容', dataIndex: 'content', ellipsis: true, search: false },
    {
      title: '患者状况',
      dataIndex: 'patientCondition',
      width: 80,
      search: false,
      render: (_, record) => {
        if (!record.patientCondition) return '-';
        const c = CONDITION_MAP[record.patientCondition];
        return <Tag color={c?.color}>{c?.text || record.patientCondition}</Tag>;
      },
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 170, valueType: 'dateTime', search: false },
    {
      title: '操作',
      key: 'option',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <a onClick={() => handleView(record.id)} style={{ fontSize: 13 }}>
            <EyeOutlined /> 查看
          </a>
          <a onClick={() => handleEdit(record.id)} style={{ fontSize: 13 }}>
            <EditOutlined /> 编辑
          </a>
          <Popconfirm title="确定删除该随访记录吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff4d4f', fontSize: 13 }}>
              <DeleteOutlined /> 删除
            </a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<FollowUpRecordListItem>
        headerTitle="随访记录"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(followUpApi.getRecordList, ({ keyword, doctorId, startDate, endDate, ...params }) => ({
          ...params,
          keyword: keyword || undefined,
          doctorId: doctorId || undefined,
          startDate: startDate || undefined,
          endDate: endDate || undefined,
        }))}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      {/* 详情抽屉 */}
      <Drawer
        title="随访记录详情"
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentRecord(null);
        }}
        width={580}
      >
        <Spin spinning={detailLoading}>
          {currentRecord ? (
            <Descriptions column={2} bordered size="small" items={[
              { key: 'patient', label: '患者', children: currentRecord.patientName || '-' },
              { key: 'doctor', label: '医生', children: currentRecord.doctorName || '-' },
              { key: 'date', label: '随访日期', children: currentRecord.followUpDate ? dayjs(currentRecord.followUpDate).format('YYYY-MM-DD') : '-' },
              { key: 'condition', label: '患者状况', children: currentRecord.patientCondition ? (
                <Tag color={CONDITION_MAP[currentRecord.patientCondition]?.color}>
                  {CONDITION_MAP[currentRecord.patientCondition]?.text || currentRecord.patientCondition}
                </Tag>
              ) : '-' },
              { key: 'content', label: '随访内容', children: currentRecord.content || '-', span: 2 },
              { key: 'nextAction', label: '下一步措施', children: currentRecord.nextAction || '-', span: 2 },
              { key: 'nextDate', label: '下次随访日期', children: currentRecord.nextFollowUpDate || '-' },
              { key: 'createdAt', label: '创建时间', children: currentRecord.createdAt ? dayjs(currentRecord.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
            ]} />
          ) : null}
        </Spin>
      </Drawer>

      {/* 编辑弹窗 */}
      <ModalForm
        title="编辑随访记录"
        open={editModalOpen}
        onOpenChange={(open) => {
          if (!open) {
            setEditModalOpen(false);
            setEditingRecord(null);
          }
        }}
        initialValues={editingRecord ? {
          content: editingRecord.content,
          patientCondition: editingRecord.patientCondition,
          nextAction: editingRecord.nextAction,
          nextFollowUpDate: editingRecord.nextFollowUpDate,
        } : undefined}
        onFinish={async (values) => {
          if (!editingRecord) return false;
          try {
            await followUpApi.updateRecord(editingRecord.id, {
              content: values.content,
              patientCondition: values.patientCondition || undefined,
              nextAction: values.nextAction || undefined,
              nextFollowUpDate: values.nextFollowUpDate || undefined,
            });
            message.success('更新成功');
            setEditModalOpen(false);
            setEditingRecord(null);
            actionRef.current?.reload();
            return true;
          } catch (error: any) {
            message.error(error.message || '更新失败');
            return false;
          }
        }}
        width={560}
        grid
        rowProps={{ gutter: 16 }}
      >
        <ProFormTextArea name="content" label="随访内容" rules={[{ required: true }]} colProps={{ span: 24 }} fieldProps={{ rows: 4 }} />
        <ProFormSelect
          name="patientCondition"
          label="患者状况"
          colProps={{ span: 12 }}
          valueEnum={{ improved: '好转', stable: '稳定', worsened: '恶化' }}
          fieldProps={{ allowClear: true, placeholder: '请选择' }}
        />
        <ProFormDatePicker name="nextFollowUpDate" label="下次随访日期" colProps={{ span: 12 }} />
        <ProFormTextArea name="nextAction" label="下一步措施" colProps={{ span: 24 }} fieldProps={{ rows: 3 }} />
      </ModalForm>
    </PageContainer>
  );
};

export default FollowUpRecordsPage;
