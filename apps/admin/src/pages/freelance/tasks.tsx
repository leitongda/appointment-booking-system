import type { ProColumns } from '@ant-design/pro-components';
import {PageContainer, ProTable, ModalForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDigit, ProFormDateTimePicker} from '@ant-design/pro-components';
import {Tag, Button, Drawer, Descriptions, message} from 'antd';
import {PlusOutlined} from '@ant-design/icons';
import {useState} from 'react';
import {freelanceTaskApi, freelancerApi} from '@hospital/api';
import type { FreelanceTask, FreelanceInteraction } from '@hospital/api';
import {createListRequest} from '@/utils/proTable';
import {useListPage} from '@/hooks/useListPage';
import {OperationButton, OperationGroup} from '@/components/ListOperations';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待发布', color: 'default' },
  published: { text: '已发布', color: 'blue' },
  indexed: { text: '已收录', color: 'green' },
  need_modify: { text: '需修改', color: 'orange' },
  rejected: { text: '已拒绝', color: 'red' },
};

const TasksPage: React.FC = () => {
  const { actionRef, reload } = useListPage();
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [interactionOpen, setInteractionOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<FreelanceTask | null>(null);
  const [interactions, setInteractions] = useState<FreelanceInteraction[]>([]);

  const handleCreate = async (values: any) => {
    try {
      await freelanceTaskApi.create(values);
      message.success('创建成功');
      setCreateOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const handleUpdate = async (values: any) => {
    if (!currentRecord) return false;
    try {
      await freelanceTaskApi.update(currentRecord.id, values);
      message.success('更新成功');
      setEditOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '更新失败');
      return false;
    }
  };

  const handleAddInteraction = async (values: any) => {
    if (!currentRecord) return false;
    try {
      await freelanceTaskApi.addInteraction({
        taskId: currentRecord.id,
        interactionType: values.interactionType,
        content: values.content,
      });
      message.success('添加成功');
      setInteractionOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  };

  const openDetail = async (record: FreelanceTask) => {
    setCurrentRecord(record);
    try {
      const data = await freelanceTaskApi.getInteractions(record.id);
      setInteractions(data);
    } catch {
      setInteractions([]);
    }
    setDetailOpen(true);
  };

  const columns: ProColumns<FreelanceTask>[] = [
    { title: '笔记标题', dataIndex: 'title', ellipsis: true },
    { title: '兼职人员', dataIndex: 'freelancerName', width: 100, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueEnum: Object.fromEntries(Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const s = STATUS_MAP[r.status] || { text: r.status, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    { title: '点赞数', dataIndex: 'likesCount', width: 80, search: false },
    { title: '评论数', dataIndex: 'commentsCount', width: 80, search: false },
    { title: '基础金额', dataIndex: 'baseAmount', width: 90, search: false, render: (_, r) => `¥${Number(r.baseAmount).toFixed(2)}` },
    { title: '补贴金额', dataIndex: 'bonusAmount', width: 90, search: false, render: (_, r) => `¥${Number(r.bonusAmount).toFixed(2)}` },
    { title: '点赞奖励', dataIndex: 'likesBonusAmount', width: 90, search: false, render: (_, r) => `¥${Number(r.likesBonusAmount).toFixed(2)}` },
    { title: '发布时间', dataIndex: 'publishedAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton type="view" permission="freelance:list" onClick={() => openDetail(record)} />
          <OperationButton type="edit" permission="freelance:update" onClick={() => { setCurrentRecord(record); setEditOpen(true); }} />
          <OperationButton type="custom" permission="freelance:create" label="互动" onClick={() => { setCurrentRecord(record); setInteractionOpen(true); }} />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<FreelanceTask>
        headerTitle="任务管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(freelanceTaskApi.getList)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="create" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新增任务
          </Button>,
        ]}
      />

      <ModalForm title="新增任务" open={createOpen} onOpenChange={setCreateOpen} onFinish={handleCreate} modalProps={{ destroyOnHidden: true }}>
        <ProFormSelect name="freelancerId" label="兼职人员" rules={[{ required: true }]}
          showSearch debounceTime={300}
          request={async ({ keyWords }) => {
            if (!keyWords || keyWords.length < 1) return [];
            const res = await freelancerApi.getList({ name: keyWords, pageSize: 20 });
            return (res.data || []).map((f: any) => ({ label: `${f.name} (${f.accountName || '-'})`, value: f.id }));
          }}
        />
        <ProFormText name="title" label="笔记标题" rules={[{ required: true }]} />
        <ProFormText name="contentUrl" label="笔记链接" />
        <ProFormDateTimePicker name="publishedAt" label="发布时间" />
        <ProFormTextArea name="remark" label="备注" />
      </ModalForm>

      <ModalForm title="编辑任务" open={editOpen} onOpenChange={setEditOpen} onFinish={handleUpdate}
        modalProps={{ destroyOnHidden: true }}
        initialValues={currentRecord ? {
          title: currentRecord.title,
          contentUrl: currentRecord.contentUrl,
          status: currentRecord.status,
          isIndexed: currentRecord.isIndexed,
          likesCount: currentRecord.likesCount,
          bonusAmount: currentRecord.bonusAmount,
          remark: currentRecord.remark,
        } : undefined}
      >
        <ProFormText name="title" label="笔记标题" rules={[{ required: true }]} />
        <ProFormText name="contentUrl" label="笔记链接" />
        <ProFormSelect name="status" label="状态"
          options={Object.entries(STATUS_MAP).map(([k, v]) => ({ label: v.text, value: k }))}
        />
        <ProFormSelect name="isIndexed" label="是否收录"
          options={[{ label: '已收录', value: true as any }, { label: '未收录', value: false as any }]}
        />
        <ProFormDigit name="likesCount" label="点赞数" min={0} fieldProps={{ precision: 0 }} />
        <ProFormDigit name="bonusAmount" label="补贴金额（5~30）" min={0} max={30} fieldProps={{ precision: 2 }} />
        <ProFormTextArea name="remark" label="备注" />
      </ModalForm>

      <ModalForm title="添加互动记录" open={interactionOpen} onOpenChange={setInteractionOpen} onFinish={handleAddInteraction} modalProps={{ destroyOnHidden: true }}>
        <ProFormSelect name="interactionType" label="互动类型" rules={[{ required: true }]}
          options={[{ label: '评论', value: 'comment' }, { label: '私信', value: 'dm' }]}
        />
        <ProFormTextArea name="content" label="互动内容" />
      </ModalForm>

      <Drawer title="任务详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={600}>
        {currentRecord && (
          <>
            <Descriptions column={1} bordered size="small" items={[
              { key: '0', label: '笔记标题', children: currentRecord.title },
              { key: '1', label: '兼职人员', children: currentRecord.freelancerName || currentRecord.freelancerId },
              { key: '2', label: '状态', children: STATUS_MAP[currentRecord.status]?.text || currentRecord.status },
              { key: '3', label: '笔记链接', children: currentRecord.contentUrl || '-' },
              { key: '4', label: '发布时间', children: currentRecord.publishedAt || '-' },
              { key: '5', label: '是否收录', children: currentRecord.isIndexed ? '是' : '否' },
              { key: '6', label: '点赞数', children: currentRecord.likesCount },
              { key: '7', label: '评论数', children: currentRecord.commentsCount },
              { key: '8', label: '基础金额', children: `¥${Number(currentRecord.baseAmount).toFixed(2)}` },
              { key: '9', label: '补贴金额', children: `¥${Number(currentRecord.bonusAmount).toFixed(2)}` },
              { key: '10', label: '点赞奖励', children: `¥${Number(currentRecord.likesBonusAmount).toFixed(2)}` },
            ]} />
            <div style={{ marginTop: 16 }}>
              <h4>互动记录（{interactions.length} 条）</h4>
              {interactions.length > 0 ? (
                <Descriptions column={1} bordered size="small" items={interactions.map((item, i) => ({
                  key: String(i),
                  label: `${item.interactionType === 'comment' ? '评论' : '私信'} - ¥${Number(item.amount).toFixed(2)}`,
                  children: item.content || '-',
                }))} />
              ) : (
                <div style={{ color: 'var(--color-text-tertiary)' }}>暂无互动记录</div>
              )}
            </div>
          </>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default TasksPage;
