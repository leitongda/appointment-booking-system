import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, Col, Dropdown, message, Modal, Popconfirm, Row, Select, Space, Tag, TreeSelect, Upload } from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  EllipsisOutlined,
  ExportOutlined,
  EyeOutlined,
  FolderOutlined,
  ImportOutlined,
  PlusOutlined,
  TagsOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useState, useRef, useEffect, useCallback } from 'react';
import GroupPanel from './components/GroupPanel';
import ContactForm from './components/ContactForm';
import ContactDetail from './components/ContactDetail';

/** 联系人类型映射 */
const CONTACT_TYPE_MAP: Record<string, { text: string; color: string }> = {
  patient: { text: '患者', color: 'blue' },
  doctor: { text: '医生', color: 'green' },
  admin: { text: '管理员', color: 'purple' },
  staff: { text: '员工', color: 'cyan' },
  external: { text: '外部联系人', color: 'orange' },
};

/** 状态映射 */
const STATUS_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '正常', color: 'success' },
  0: { text: '禁用', color: 'error' },
};

const ContactsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | undefined>();
  const [formOpen, setFormOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<Record<string, any> | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailContactId, setDetailContactId] = useState<string | null>(null);

  // 批量操作相关状态
  const [moveGroupOpen, setMoveGroupOpen] = useState(false);
  const [batchTagOpen, setBatchTagOpen] = useState(false);
  const [groups, setGroups] = useState<any[]>([]);
  const [tags, setTags] = useState<any[]>([]);
  const [selectedMoveGroupId, setSelectedMoveGroupId] = useState<string | undefined>();
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);

  // 导入相关状态
  const [importOpen, setImportOpen] = useState(false);

  // 加载分组和标签
  const loadGroupsAndTags = useCallback(async () => {
    const token = localStorage.getItem('token');
    try {
      const [groupsRes, tagsRes] = await Promise.all([
        fetch('/api/v1/contact-groups', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/v1/contact-tags', { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      const groupsData = await groupsRes.json();
      const tagsData = await tagsRes.json();
      setGroups(groupsData.data || groupsData || []);
      setTags(tagsData.data || tagsData || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadGroupsAndTags();
  }, [loadGroupsAndTags]);

  /** 批量删除 */
  const handleBatchDelete = async () => {
    try {
      await fetch('/api/v1/contacts/batch-delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ ids: selectedRowKeys }),
      });
      message.success(`已删除 ${selectedRowKeys.length} 个联系人`);
      setSelectedRowKeys([]);
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '删除失败');
    }
  };

  /** 删除单个联系人 */
  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/v1/contacts/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      message.success('已删除');
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '删除失败');
    }
  };

  /** 批量移动分组 */
  const handleBatchMoveGroup = async () => {
    if (!selectedMoveGroupId) {
      message.warning('请选择目标分组');
      return;
    }
    try {
      await fetch('/api/v1/contacts/batch-move-group', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ ids: selectedRowKeys, group_id: selectedMoveGroupId }),
      });
      message.success(`已移动 ${selectedRowKeys.length} 个联系人`);
      setMoveGroupOpen(false);
      setSelectedMoveGroupId(undefined);
      setSelectedRowKeys([]);
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    }
  };

  /** 批量打标签 */
  const handleBatchAddTags = async () => {
    if (selectedTagIds.length === 0) {
      message.warning('请选择标签');
      return;
    }
    try {
      await fetch('/api/v1/contacts/batch-add-tags', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ ids: selectedRowKeys, tag_ids: selectedTagIds }),
      });
      message.success(`已为 ${selectedRowKeys.length} 个联系人添加标签`);
      setBatchTagOpen(false);
      setSelectedTagIds([]);
      setSelectedRowKeys([]);
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    }
  };

  /** 导出联系人 */
  const handleExport = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/v1/contacts/export', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `联系人_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (e: any) {
      message.error(e.message || '导出失败');
    }
  };

  /** 导入联系人 */
  const handleImport = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('/api/v1/contacts/import', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: formData,
      });
      const data = await res.json();
      if (data.data?.fail_count > 0) {
        message.warning(`导入完成：成功 ${data.data.success_count} 条，失败 ${data.data.fail_count} 条`);
      } else {
        message.success(`导入成功：${data.data?.success_count || 0} 条`);
      }
      setImportOpen(false);
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '导入失败');
    }
    return false; // 阻止 Upload 自动上传
  };

  /** 构建分组树数据 */
  const buildGroupTreeData = (items: any[]): any[] =>
    items.map((g) => ({
      title: g.name,
      value: g.id,
      children: g.children ? buildGroupTreeData(g.children) : undefined,
    }));

  /** 表格列定义 */
  const columns: ProColumns[] = [
    {
      title: '姓名',
      dataIndex: 'name',
      width: 160,
      ellipsis: true,
      render: (_, r) => (
        <Space>
          {r.avatar ? (
            <img src={r.avatar} alt="" style={{ width: 24, height: 24, borderRadius: '50%' }} />
          ) : null}
          <span>{r.name}</span>
          {r.nickname && <span style={{ color: '#999', fontSize: 12 }}>({r.nickname})</span>}
        </Space>
      ),
    },
    { title: '手机号', dataIndex: 'phone', width: 130, search: false },
    { title: '邮箱', dataIndex: 'email', width: 180, ellipsis: true, search: false },
    {
      title: '类型',
      dataIndex: 'contactType',
      width: 100,
      valueEnum: Object.fromEntries(
        Object.entries(CONTACT_TYPE_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const t = CONTACT_TYPE_MAP[r.contactType] || { text: r.contactType, color: 'default' };
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '分组',
      dataIndex: 'groups',
      width: 150,
      search: false,
      render: (_, r) =>
        r.groups?.map((g: any) => (
          <Tag key={g.id} color="blue">{g.name}</Tag>
        )),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 150,
      search: false,
      render: (_, r) =>
        r.tags?.map((t: any) => (
          <Tag key={t.id} color={t.color || 'default'}>{t.name}</Tag>
        )),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const s = STATUS_MAP[r.status] || { text: '未知', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      sorter: true,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, r) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setDetailContactId(r.id);
              setDetailOpen(true);
            }}
          >
            详情
          </Button>
          <Dropdown
            menu={{
              items: [
                { key: 'edit', icon: <EditOutlined />, label: '编辑' },
                { key: 'delete', icon: <DeleteOutlined />, label: '删除', danger: true },
              ],
              onClick: ({ key }) => {
                if (key === 'edit') {
                  setEditingContact(r);
                  setFormOpen(true);
                } else if (key === 'delete') {
                  handleDelete(r.id);
                }
              },
            }}
          >
            <Button type="link" size="small" icon={<EllipsisOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <Row gutter={16}>
        {/* 左侧分组面板 */}
        <Col span={5}>
          <GroupPanel
            selectedGroupId={selectedGroupId}
            onGroupSelect={(id) => {
              setSelectedGroupId(id);
              actionRef.current?.reload();
            }}
          />
        </Col>

        {/* 右侧联系人列表 */}
        <Col span={19}>
          <ProTable
            actionRef={actionRef}
            rowKey="id"
            columns={columns}
            request={async (params) => {
              const searchParams = new URLSearchParams();
              searchParams.set('page', String(params.current || 1));
              searchParams.set('page_size', String(params.pageSize || 20));
              if (params.name) searchParams.set('keyword', params.name);
              if (params.contactType) searchParams.set('contact_type', params.contactType);
              if (params.status !== undefined && params.status !== null)
                searchParams.set('status', String(params.status));
              if (selectedGroupId) searchParams.set('group_id', selectedGroupId);

              const res = await fetch(`/api/v1/contacts?${searchParams}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
              });
              const data = await res.json();
              const items = data.data?.items || data.items || [];
              return { data: items, success: true, total: data.data?.total || data.total || 0 };
            }}
            pagination={{ defaultPageSize: 20 }}
            search={{ labelWidth: 'auto' }}
            scroll={{ x: 1200 }}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys as string[]),
            }}
            toolBarRender={() => [
              selectedRowKeys.length > 0 ? (
                <Space key="batch-actions">
                  <Popconfirm
                    title={`确认删除 ${selectedRowKeys.length} 个联系人？`}
                    onConfirm={handleBatchDelete}
                  >
                    <Button danger icon={<DeleteOutlined />}>
                      批量删除 ({selectedRowKeys.length})
                    </Button>
                  </Popconfirm>
                  <Button icon={<FolderOutlined />} onClick={() => setMoveGroupOpen(true)}>
                    移动分组 ({selectedRowKeys.length})
                  </Button>
                  <Button icon={<TagsOutlined />} onClick={() => setBatchTagOpen(true)}>
                    打标签 ({selectedRowKeys.length})
                  </Button>
                </Space>
              ) : null,
              <Button key="import" icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                导入
              </Button>,
              <Button key="export" icon={<ExportOutlined />} onClick={handleExport}>
                导出
              </Button>,
              <Button
                key="create"
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingContact(null);
                  setFormOpen(true);
                }}
              >
                新建联系人
              </Button>,
            ]}
          />
        </Col>
      </Row>

      {/* 新建/编辑联系人 */}
      <ContactForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={() => {
          setFormOpen(false);
          actionRef.current?.reload();
        }}
        initialValues={editingContact}
      />

      {/* 联系人详情 */}
      <ContactDetail
        contactId={detailContactId}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false);
          setDetailContactId(null);
        }}
      />

      {/* 批量移动分组 Modal */}
      <Modal
        title="批量移动分组"
        open={moveGroupOpen}
        onOk={handleBatchMoveGroup}
        onCancel={() => {
          setMoveGroupOpen(false);
          setSelectedMoveGroupId(undefined);
        }}
      >
        <div style={{ marginBottom: 8 }}>
          将 {selectedRowKeys.length} 个联系人移动到：
        </div>
        <TreeSelect
          style={{ width: '100%' }}
          placeholder="选择目标分组"
          treeData={buildGroupTreeData(groups)}
          value={selectedMoveGroupId}
          onChange={setSelectedMoveGroupId}
          allowClear
        />
      </Modal>

      {/* 批量打标签 Modal */}
      <Modal
        title="批量打标签"
        open={batchTagOpen}
        onOk={handleBatchAddTags}
        onCancel={() => {
          setBatchTagOpen(false);
          setSelectedTagIds([]);
        }}
      >
        <div style={{ marginBottom: 8 }}>
          为 {selectedRowKeys.length} 个联系人添加标签：
        </div>
        <Select
          mode="multiple"
          style={{ width: '100%' }}
          placeholder="选择标签"
          value={selectedTagIds}
          onChange={setSelectedTagIds}
          options={tags.map((t: any) => ({
            label: (
              <Space>
                <Tag color={t.color || 'default'}>{t.name}</Tag>
              </Space>
            ),
            value: t.id,
          }))}
        />
      </Modal>

      {/* 导入联系人 Modal */}
      <Modal
        title="导入联系人"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        footer={null}
      >
        <div style={{ marginBottom: 16 }}>
          <p>支持 .xlsx、.xls、.csv 格式，列顺序：姓名、昵称、性别、手机号、邮箱、联系人类型、职位、所属机构、备注</p>
        </div>
        <Upload.Dragger
          accept=".xlsx,.xls,.csv"
          beforeUpload={(file) => {
            handleImport(file);
            return false;
          }}
          showUploadList={false}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        </Upload.Dragger>
      </Modal>
    </PageContainer>
  );
};

export default ContactsPage;
