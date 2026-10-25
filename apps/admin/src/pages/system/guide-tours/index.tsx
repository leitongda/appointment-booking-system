/**
 * 操作指引管理 - 列表页
 *
 * 平台管理员可创建、编辑、发布/下线、删除操作指引。
 */
import {PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, PauseCircleOutlined} from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {PageContainer, ProTable} from '@ant-design/pro-components';
import {App, Tag, Popconfirm, Button, Space, Typography} from 'antd';
import {useRef, useCallback, useMemo} from 'react';
import {history} from '@umijs/max';
import {adminGuideToursApi} from '@hospital/api';
import type { GuideTourListItem } from '@hospital/api';
import {t} from '@/utils/locale';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '草稿', color: 'default' },
  1: { text: '已发布', color: 'success' },
};

const GuideToursPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();

  const handleDelete = useCallback(async (id: string) => {
    try {
      await adminGuideToursApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  }, [message]);

  const handleToggleStatus = useCallback(async (id: string, currentStatus: number) => {
    try {
      const newStatus = currentStatus === 1 ? 0 : 1;
      await adminGuideToursApi.updateStatus(id, newStatus);
      message.success(newStatus === 1 ? '已发布' : '已下线');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  }, [message]);

  const columns = useMemo<ProColumns<GuideTourListItem>[]>(() => [
    {
      title: '指引名称',
      dataIndex: 'title',
      render: (_, record) => t(record.title),
      fieldProps: {
        placeholder: '搜索指引名称',
      },
      hideInTable: false,
      hideInSearch: true,
    },
    {
      title: '标识码',
      dataIndex: 'code',
      copyable: true,
      ellipsis: true,
    },
    {
      title: '步骤数',
      dataIndex: 'stepCount',
      hideInSearch: true,
      width: 100,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'status',
      hideInSearch: true,
      width: 100,
      render: (_, record) => {
        const cfg = STATUS_MAP[record.status] || STATUS_MAP[0];
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
      filters: true,
      valueEnum: {
        0: { text: '草稿' },
        1: { text: '已发布' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      hideInSearch: true,
      width: 180,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Typography.Link
            onClick={() => history.push(`/system/guide-tours/${record.id}/edit`)}
          >
            <EditOutlined /> 编辑
          </Typography.Link>
          <Typography.Link
            onClick={() => handleToggleStatus(record.id, record.status)}
          >
            {record.status === 1 ? (
              <><PauseCircleOutlined /> 下线</>
            ) : (
              <><PlayCircleOutlined /> 发布</>
            )}
          </Typography.Link>
          <Popconfirm
            title="确定删除此指引？"
            description="删除后不可恢复"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Typography.Link type="danger">
              <DeleteOutlined /> 删除
            </Typography.Link>
          </Popconfirm>
        </Space>
      ),
    },
  ], [handleDelete, handleToggleStatus]);

  return (
    <PageContainer title="操作指引管理">
      <ProTable<GuideTourListItem>
        headerTitle="指引列表"
        actionRef={actionRef}
        rowKey="id"
        search={false}
        request={async (params) => {
          try {
            const { data, total } = await adminGuideToursApi.getList({
              page: params.current,
              pageSize: params.pageSize,
              status: params.status,
            });
            return {
              data: data || [],
              total: total || 0,
              success: true,
            };
          } catch {
            return { data: [], total: 0, success: false };
          }
        }}
        columns={columns}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/system/guide-tours/create')}
          >
            新建指引
          </Button>,
        ]}
      />
    </PageContainer>
  );
};

export default GuideToursPage;
