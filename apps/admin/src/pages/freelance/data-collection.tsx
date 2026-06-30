import { PageContainer } from '@ant-design/pro-components';
import { Card, Table, InputNumber, Button, Switch, Space, message, Upload, Tooltip } from 'antd';
import { UploadOutlined, SaveOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback } from 'react';
import { freelanceTaskApi, freelanceSettlementApi } from '@hospital/api';
import type { FreelanceTask } from '@hospital/api';
import { App } from 'antd';

interface EditableTask extends FreelanceTask {
  editLikes?: number;
  editComments?: number;
  editIndexed?: boolean;
  screenshotUrl?: string;
}

const DataCollectionPage: React.FC = () => {
  const { message: msg } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tasks, setTasks] = useState<EditableTask[]>([]);
  const [changedIds, setChangedIds] = useState<Set<string>>(new Set());

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await freelanceTaskApi.getList({ status: 'published', pageSize: 100 });
      setTasks((res.data || []).map((t: FreelanceTask) => ({
        ...t,
        editLikes: t.likesCount,
        editComments: t.commentsCount,
        editIndexed: t.isIndexed,
      })));
    } catch (error: any) {
      msg.error(error.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [msg]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const handleChange = (id: string, field: string, value: any) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, [field]: value } : t));
    setChangedIds(prev => new Set(prev).add(id));
  };

  const handleSave = async () => {
    const updates = tasks
      .filter(t => changedIds.has(t.id))
      .map(t => ({
        taskId: t.id,
        likesCount: t.editLikes,
        commentsCount: t.editComments,
        isIndexed: t.editIndexed,
        screenshotUrl: t.screenshotUrl,
      }));

    if (updates.length === 0) {
      msg.warning('没有需要保存的更改');
      return;
    }

    setSaving(true);
    try {
      const result = await freelanceSettlementApi.batchUpdateEngagement(updates);

      if (result.updated > 0) {
        msg.success(`已更新 ${result.updated} 条记录`);
        setChangedIds(new Set());
        fetchTasks();
      }
      if (result.errors?.length > 0) {
        msg.warning(`${result.errors.length} 条更新失败`);
      }
    } catch (error: any) {
      msg.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: '笔记标题', dataIndex: 'title', ellipsis: true, width: 200 },
    { title: '兼职人员', dataIndex: 'freelancerName', width: 100 },
    {
      title: '点赞数',
      dataIndex: 'editLikes',
      width: 120,
      render: (_: any, record: EditableTask) => (
        <InputNumber
          size="small"
          min={0}
          value={record.editLikes}
          onChange={(v) => handleChange(record.id, 'editLikes', v ?? 0)}
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: '评论数',
      dataIndex: 'editComments',
      width: 120,
      render: (_: any, record: EditableTask) => (
        <InputNumber
          size="small"
          min={0}
          value={record.editComments}
          onChange={(v) => handleChange(record.id, 'editComments', v ?? 0)}
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: '是否收录',
      dataIndex: 'editIndexed',
      width: 90,
      render: (_: any, record: EditableTask) => (
        <Switch
          checked={record.editIndexed}
          onChange={(v) => handleChange(record.id, 'editIndexed', v)}
        />
      ),
    },
    {
      title: '点赞奖励',
      width: 90,
      render: (_: any, record: EditableTask) => (
        <span style={{ color: (record.editLikes ?? 0) >= 50 ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
          {(record.editLikes ?? 0) >= 50 ? '¥10.00' : '-'}
        </span>
      ),
    },
    {
      title: '截图',
      width: 80,
      render: (_: any, record: EditableTask) => (
        <Tooltip title={record.screenshotUrl || '未上传'}>
          <Upload
            showUploadList={false}
            beforeUpload={() => false}
            onChange={(info) => {
              if (info.file) {
                handleChange(record.id, 'screenshotUrl', info.file.name);
              }
            }}
          >
            <Button size="small" icon={<UploadOutlined />} />
          </Upload>
        </Tooltip>
      ),
    },
  ];

  return (
    <PageContainer>
      <Card
        title="数据采集"
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSave}
            disabled={changedIds.size === 0}
          >
            保存更改 ({changedIds.size})
          </Button>
        }
      >
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 800 }}
        />
      </Card>
    </PageContainer>
  );
};

export default DataCollectionPage;
