import { Drawer, Button, List, Tag, Popconfirm, Space, Empty } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { memo, useState } from 'react';
import ListenerForm from './ListenerForm';
import type { ListenerConfig } from './ListenerForm';

const EVENT_LABEL_MAP: Record<string, string> = {
  'process.start': '流程启动',
  'process.end': '流程结束',
  'process.cancel': '流程取消',
  'process.reject': '流程拒绝',
};

const ACTION_TYPE_LABEL_MAP: Record<string, string> = {
  webhook: 'Webhook',
  notification: '站内通知',
  sms: '短信',
  callback: '回调',
};

const ACTION_TYPE_COLOR_MAP: Record<string, string> = {
  webhook: 'blue',
  notification: 'green',
  sms: 'orange',
  callback: 'purple',
};

interface GlobalListenerDrawerProps {
  open: boolean;
  onClose: () => void;
  listeners: ListenerConfig[];
  onChange: (listeners: ListenerConfig[]) => void;
}

const GlobalListenerDrawer: React.FC<GlobalListenerDrawerProps> = memo(({
  open,
  onClose,
  listeners,
  onChange,
}) => {
  const [editing, setEditing] = useState<ListenerConfig | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleAdd = () => {
    setEditing(null);
    setShowForm(true);
  };

  const handleEdit = (item: ListenerConfig) => {
    setEditing(item);
    setShowForm(true);
  };

  const handleDelete = (id: string) => {
    onChange(listeners.filter((l) => l.id !== id));
  };

  const handleSubmit = (values: ListenerConfig) => {
    if (editing?.id) {
      onChange(listeners.map((l) => (l.id === editing.id ? { ...values, id: editing.id } : l)));
    } else {
      onChange([...listeners, { ...values, id: `listener_${Date.now()}` }]);
    }
    setShowForm(false);
    setEditing(null);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditing(null);
  };

  return (
    <Drawer
      title="流程设置"
      width={400}
      open={open}
      onClose={onClose}
      extra={
        !showForm && (
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleAdd}>
            添加监听器
          </Button>
        )
      }
    >
      {showForm ? (
        <ListenerForm
          initialValues={editing || undefined}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      ) : listeners.length === 0 ? (
        <Empty description="暂无全局监听器" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          size="small"
          dataSource={listeners}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button
                  key="edit"
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(item)}
                />,
                <Popconfirm
                  key="delete"
                  title="确定删除?"
                  onConfirm={() => handleDelete(item.id!)}
                >
                  <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                title={item.label || item.config?.callbackName || '-'}
                description={
                  <Space size={4}>
                    <Tag>{EVENT_LABEL_MAP[item.event] || item.event}</Tag>
                    <Tag color={ACTION_TYPE_COLOR_MAP[item.actionType] || 'default'}>
                      {ACTION_TYPE_LABEL_MAP[item.actionType] || item.actionType}
                    </Tag>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Drawer>
  );
});

GlobalListenerDrawer.displayName = 'GlobalListenerDrawer';

export default GlobalListenerDrawer;
