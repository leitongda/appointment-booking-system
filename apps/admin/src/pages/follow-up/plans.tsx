import {PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined} from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormDigit, ProFormList} from '@ant-design/pro-components';
import {App, Button, Drawer, Descriptions, Popconfirm, Space, Spin, Tag} from 'antd';
import {useRef, useState, useCallback} from 'react';
import {departmentApi, followUpApi} from '@hospital/api';
import type { FollowUpPlan, FollowUpPlanListItem } from '@hospital/api';
import {createListRequest} from '@/utils/proTable';
import {fetchAllData} from '@/utils/fetchAllData';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '启用', color: 'success' },
  0: { text: '停用', color: 'default' },
};

const FollowUpPlansPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<FollowUpPlan | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<FollowUpPlan | null>(null);

  const handleView = async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await followUpApi.getPlanDetail(id);
      setCurrentPlan(result);
    } catch (error: any) {
      message.error(error.message || '加载详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleEdit = async (id: string) => {
    try {
      const result = await followUpApi.getPlanDetail(id);
      setEditingPlan(result);
      setModalOpen(true);
    } catch (error: any) {
      message.error(error.message || '加载详情失败');
    }
  };

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await followUpApi.deletePlan(id);
        message.success('删除成功');
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '删除失败');
      }
    },
    [message],
  );

  const columns: ProColumns<FollowUpPlanListItem>[] = [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '计划名称/诊断名称' },
    },
    {
      title: '科室',
      dataIndex: 'departmentId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: { showSearch: true, optionFilterProp: 'label', placeholder: '请选择科室' },
      request: async () => {
        try {
          const depts = await fetchAllData((p, ps) => departmentApi.getList({ page: p, pageSize: ps }));
          return [{ label: '全部科室', value: '' }, ...depts.map((d: any) => ({ label: d.name, value: d.id }))];
        } catch {
          return [];
        }
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      hideInTable: true,
      valueType: 'select',
      valueEnum: { '': { text: '全部' }, '1': { text: '启用' }, '0': { text: '停用' } },
    },
    { title: '计划名称', dataIndex: 'name', width: 200 },
    { title: '科室', dataIndex: 'departmentName', width: 120, search: false },
    { title: '诊断', dataIndex: 'diagnosisName', width: 150, search: false },
    { title: '步骤数', dataIndex: 'stepCount', width: 80, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      search: false,
      render: (_, record) => {
        const s = STATUS_MAP[record.status ?? 1];
        return <Tag color={s.color}>{s.text}</Tag>;
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
          <Popconfirm title="确定删除该随访计划吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'var(--color-error)', fontSize: 13 }}>
              <DeleteOutlined /> 删除
            </a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<FollowUpPlanListItem>
        headerTitle="随访计划"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(followUpApi.getPlanList, ({ keyword, departmentId, status, ...params }) => ({
          ...params,
          keyword: keyword || undefined,
          departmentId: departmentId || undefined,
          status: status !== undefined && status !== '' ? Number(status) : undefined,
        }))}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingPlan(null);
              setModalOpen(true);
            }}
          >
            新增计划
          </Button>,
        ]}
      />

      {/* 详情抽屉 */}
      <Drawer
        title={currentPlan ? `随访计划 · ${currentPlan.name}` : '随访计划详情'}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentPlan(null);
        }}
        width={640}
      >
        <Spin spinning={detailLoading}>
          {currentPlan ? (
            <>
              <Descriptions column={2} bordered size="small" items={[
                { key: 'name', label: '计划名称', children: currentPlan.name, span: 2 },
                { key: 'dept', label: '科室', children: currentPlan.departmentName || '-' },
                { key: 'diag', label: '诊断', children: currentPlan.diagnosisName || '-' },
                { key: 'status', label: '状态', children: <Tag color={STATUS_MAP[currentPlan.status ?? 1]?.color}>{STATUS_MAP[currentPlan.status ?? 1]?.text}</Tag> },
                { key: 'desc', label: '描述', children: currentPlan.description || '-', span: 2 },
              ]} />
              <div style={{ marginTop: 16, fontWeight: 500 }}>随访步骤</div>
              <ProTable
                dataSource={currentPlan.steps || []}
                columns={[
                  { title: '序号', dataIndex: 'stepOrder', width: 60 },
                  { title: '名称', dataIndex: 'name', width: 150 },
                  { title: '距就诊天数', dataIndex: 'daysAfterVisit', width: 100 },
                  { title: '说明', dataIndex: 'description', ellipsis: true },
                ]}
                rowKey="id"
                search={false}
                pagination={false}
                size="small"
                style={{ marginTop: 8 }}
              />
            </>
          ) : null}
        </Spin>
      </Drawer>

      {/* 创建/编辑弹窗 */}
      <ModalForm
        title={editingPlan ? `编辑计划 · ${editingPlan.name}` : '新增随访计划'}
        open={modalOpen}
        onOpenChange={(open) => {
          if (!open) {
            setModalOpen(false);
            setEditingPlan(null);
          }
        }}
        initialValues={editingPlan ? {
          name: editingPlan.name,
          description: editingPlan.description,
          departmentId: editingPlan.departmentId,
          diagnosisCode: editingPlan.diagnosisCode,
          diagnosisName: editingPlan.diagnosisName,
          status: editingPlan.status ?? 1,
          steps: editingPlan.steps?.map((s) => ({
            name: s.name,
            stepOrder: s.stepOrder,
            daysAfterVisit: s.daysAfterVisit,
            description: s.description,
          })) || [],
        } : { status: 1, steps: [{ stepOrder: 1, name: '首次随访', daysAfterVisit: 7 }] }}
        onFinish={async (values) => {
          try {
            if (editingPlan) {
              await followUpApi.updatePlan(editingPlan.id, {
                name: values.name,
                description: values.description,
                departmentId: values.departmentId || undefined,
                diagnosisCode: values.diagnosisCode || undefined,
                diagnosisName: values.diagnosisName || undefined,
                status: values.status,
              });
              // 更新步骤
              if (values.steps?.length) {
                await followUpApi.updatePlanSteps(
                  editingPlan.id,
                  values.steps.map((s: any, i: number) => ({
                    stepOrder: s.stepOrder ?? i + 1,
                    name: s.name,
                    daysAfterVisit: s.daysAfterVisit,
                    description: s.description,
                  })),
                );
              }
              message.success('更新成功');
            } else {
              await followUpApi.createPlan({
                name: values.name,
                description: values.description || undefined,
                departmentId: values.departmentId || undefined,
                diagnosisCode: values.diagnosisCode || undefined,
                diagnosisName: values.diagnosisName || undefined,
                steps: (values.steps || []).map((s: any, i: number) => ({
                  stepOrder: s.stepOrder ?? i + 1,
                  name: s.name,
                  daysAfterVisit: s.daysAfterVisit,
                  description: s.description,
                })),
              });
              message.success('创建成功');
            }
            setModalOpen(false);
            setEditingPlan(null);
            actionRef.current?.reload();
            return true;
          } catch (error: any) {
            message.error(error.message || '操作失败');
            return false;
          }
        }}
        width={720}
        grid
        rowProps={{ gutter: 16 }}
      >
        <ProFormText name="name" label="计划名称" rules={[{ required: true }]} colProps={{ span: 16 }} />
        <ProFormSelect
          name="status"
          label="状态"
          colProps={{ span: 8 }}
          valueEnum={{ 1: '启用', 0: '停用' }}
          rules={[{ required: true }]}
        />
        <ProFormSelect
          name="departmentId"
          label="关联科室"
          colProps={{ span: 12 }}
          fieldProps={{ showSearch: true, optionFilterProp: 'label', allowClear: true, placeholder: '不限' }}
          request={async () => {
            try {
              const depts = await fetchAllData((p, ps) => departmentApi.getList({ page: p, pageSize: ps }));
              return depts.map((d: any) => ({ label: d.name, value: d.id }));
            } catch {
              return [];
            }
          }}
        />
        <ProFormText name="diagnosisCode" label="诊断编码" colProps={{ span: 6 }} />
        <ProFormText name="diagnosisName" label="诊断名称" colProps={{ span: 6 }} />
        <ProFormTextArea name="description" label="描述" colProps={{ span: 24 }} fieldProps={{ rows: 2 }} />

        <ProFormList
          name="steps"
          label="随访步骤"
          creatorButtonProps={{ creatorButtonText: '添加步骤' }}
          min={1}
          copyIconProps={false}
          colProps={{ span: 24 }}
          itemRender={({ listDom }) => (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>{listDom}</div>
          )}
        >
          <ProFormDigit name="stepOrder" label="序号" min={1} rules={[{ required: true }]} width={80} />
          <ProFormText name="name" label="步骤名称" rules={[{ required: true }]} width={180} />
          <ProFormDigit name="daysAfterVisit" label="距就诊天数" min={0} rules={[{ required: true }]} width={130} />
          <ProFormText name="description" label="说明" width={200} />
        </ProFormList>
      </ModalForm>
    </PageContainer>
  );
};

export default FollowUpPlansPage;
