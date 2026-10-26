/**
 * 共享弹窗：按同事（管理员）或按角色授予 read / edit；仅 owner 或 knowledge:manage 可用
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Form, List, Modal, Popconfirm, Radio, Select, Space, Tag, Typography } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { adminApi, knowledgeApi } from '@hospital/api';
import type { KnowledgeShare, KnowledgeShareGrantee, KnowledgeSharePermission } from '@hospital/api';

interface ShareModalProps {
  kbId: string | null;
  kbName?: string;
  onClose: () => void;
}

interface GranteeOption {
  value: string;
  label: string;
}

const PERMISSION_TEXT: Record<KnowledgeSharePermission, string> = { read: '只读', edit: '可编辑' };
const GRANTEE_TEXT: Record<KnowledgeShareGrantee, string> = { admin: '同事', role: '角色' };

const ShareModal: React.FC<ShareModalProps> = ({ kbId, kbName, onClose }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm<{ granteeType: KnowledgeShareGrantee; granteeId: string; permission: KnowledgeSharePermission }>();
  const [shares, setShares] = useState<KnowledgeShare[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [adminOptions, setAdminOptions] = useState<GranteeOption[]>([]);
  const [roleOptions, setRoleOptions] = useState<GranteeOption[]>([]);
  const granteeType = Form.useWatch('granteeType', form) ?? 'admin';

  const loadShares = useCallback(async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      setShares(await knowledgeApi.listShares(kbId));
    } catch (err: any) {
      message.error(err?.message || '加载共享列表失败');
    } finally {
      setLoading(false);
    }
  }, [kbId, message]);

  useEffect(() => {
    if (!kbId) return;
    void loadShares();
    form.setFieldsValue({ granteeType: 'admin', permission: 'read', granteeId: undefined });
    void (async () => {
      try {
        const [admins, roles] = await Promise.all([
          adminApi.getAdmins({ page: 1, pageSize: 200, status: 1 }),
          adminApi.getAllRoles(),
        ]);
        setAdminOptions(
          (admins.data ?? []).map((item) => ({ value: item.id, label: item.name ? `${item.name}（${item.username}）` : item.username })),
        );
        setRoleOptions((roles ?? []).map((role) => ({ value: role.id, label: role.name })));
      } catch (err: any) {
        message.error(err?.message || '加载同事/角色列表失败');
      }
    })();
  }, [kbId, form, loadShares, message]);

  const handleAdd = async () => {
    if (!kbId) return;
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await knowledgeApi.addShare(kbId, values);
      message.success('已共享');
      form.setFieldValue('granteeId', undefined);
      await loadShares();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.message || '共享失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (share: KnowledgeShare) => {
    try {
      await knowledgeApi.removeShare(share.id);
      message.success('已撤销共享');
      await loadShares();
    } catch (err: any) {
      message.error(err?.message || '撤销失败');
    }
  };

  return (
    <Modal title={`共享知识库${kbName ? `：${kbName}` : ''}`} open={!!kbId} onCancel={onClose} footer={null} width={640} destroyOnHidden>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        只读：可检索与预览；可编辑：可上传、整理目录、重新处理失败文档。被共享者不能再分享或删除知识库。
      </Typography.Paragraph>
      <Form form={form} layout="inline" style={{ marginBottom: 16, rowGap: 8 }}>
        <Form.Item name="granteeType" initialValue="admin">
          <Radio.Group
            optionType="button"
            options={[
              { label: '按同事', value: 'admin' },
              { label: '按角色', value: 'role' },
            ]}
            onChange={() => form.setFieldValue('granteeId', undefined)}
          />
        </Form.Item>
        <Form.Item name="granteeId" rules={[{ required: true, message: '请选择共享对象' }]} style={{ minWidth: 220 }}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={granteeType === 'role' ? '选择角色' : '选择同事'}
            options={granteeType === 'role' ? roleOptions : adminOptions}
          />
        </Form.Item>
        <Form.Item name="permission" initialValue="read">
          <Select
            style={{ width: 110 }}
            options={[
              { label: '只读', value: 'read' },
              { label: '可编辑', value: 'edit' },
            ]}
          />
        </Form.Item>
        <Form.Item>
          <Button type="primary" loading={submitting} onClick={handleAdd}>
            添加
          </Button>
        </Form.Item>
      </Form>
      <List
        loading={loading}
        size="small"
        dataSource={shares}
        locale={{ emptyText: '尚未共享给任何人' }}
        renderItem={(share) => (
          <List.Item
            key={share.id}
            actions={[
              <Popconfirm key="remove" title="撤销后对方将立即不可见，确定？" onConfirm={() => handleRemove(share)}>
                <Button type="link" danger size="small" icon={<DeleteOutlined />}>
                  撤销
                </Button>
              </Popconfirm>,
            ]}
          >
            <Space>
              <Tag>{GRANTEE_TEXT[share.granteeType]}</Tag>
              <span>{share.granteeName || share.granteeId}</span>
              <Tag color={share.permission === 'edit' ? 'green' : 'default'}>{PERMISSION_TEXT[share.permission]}</Tag>
            </Space>
          </List.Item>
        )}
      />
    </Modal>
  );
};

export default ShareModal;
