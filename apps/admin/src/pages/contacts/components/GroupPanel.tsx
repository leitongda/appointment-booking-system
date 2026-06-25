import { Button, Card, Input, message, Modal, Space, Tag, Tree } from 'antd';
import { FolderOutlined, PlusOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback } from 'react';
import type { DataNode } from 'antd/es/tree';

/** 分组类型 */
export interface GroupItem {
  id: string;
  name: string;
  parent_id: string | null;
  children?: GroupItem[];
  contact_count?: number;
}

interface GroupPanelProps {
  /** 选中的分组 ID */
  selectedGroupId?: string;
  /** 分组选中变更 */
  onGroupSelect: (groupId: string | undefined) => void;
}

/** 获取 token */
const getToken = () => localStorage.getItem('token') || '';

/** 构建树数据 */
const buildTreeData = (items: GroupItem[]): DataNode[] =>
  items.map((g) => ({
    key: g.id,
    title: (
      <Space size={4}>
        <FolderOutlined />
        <span>{g.name}</span>
        {g.contact_count ? <Tag>{g.contact_count}</Tag> : null}
      </Space>
    ),
    children: g.children ? buildTreeData(g.children) : undefined,
  }));

const GroupPanel: React.FC<GroupPanelProps> = ({ selectedGroupId, onGroupSelect }) => {
  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupItem | null>(null);
  const [form, setForm] = useState({ name: '', description: '' });

  /** 加载分组树 */
  const loadGroups = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/contact-groups', {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      setGroups(data.data || data || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  /** 创建/更新分组 */
  const handleSubmit = async () => {
    if (!form.name.trim()) {
      message.warning('请输入分组名称');
      return;
    }
    try {
      const url = editingGroup
        ? `/api/v1/contact-groups/${editingGroup.id}`
        : '/api/v1/contact-groups';
      const method = editingGroup ? 'PUT' : 'POST';
      await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(form),
      });
      message.success(editingGroup ? '更新成功' : '创建成功');
      setModalOpen(false);
      setForm({ name: '', description: '' });
      setEditingGroup(null);
      loadGroups();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    }
  };

  /** 删除分组 */
  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/v1/contact-groups/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      message.success('删除成功');
      if (selectedGroupId === id) onGroupSelect(undefined);
      loadGroups();
    } catch (e: any) {
      message.error(e.message || '删除失败');
    }
  };

  return (
    <>
      <Card
        title="分组"
        size="small"
        extra={
          <Button
            type="link"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingGroup(null);
              setForm({ name: '', description: '' });
              setModalOpen(true);
            }}
          >
            新建
          </Button>
        }
      >
        <Tree
          showLine
          blockNode
          selectedKeys={selectedGroupId ? [selectedGroupId] : []}
          onSelect={(keys) => {
            const key = keys[0] as string | undefined;
            onGroupSelect(key === selectedGroupId ? undefined : key);
          }}
          treeData={buildTreeData(groups)}
        />
      </Card>

      <Modal
        title={editingGroup ? '编辑分组' : '新建分组'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Input
            placeholder="分组名称"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
          />
          <Input.TextArea
            placeholder="分组描述（选填）"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
          />
        </div>
      </Modal>
    </>
  );
};

export default GroupPanel;
