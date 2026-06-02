/** 低代码页面管理列表 */

import React, { useRef, useCallback } from 'react';
import { history } from '@umijs/max';
import { PageContainer } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Popconfirm, message, Space } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, SendOutlined, CopyOutlined } from '@ant-design/icons';
import { lowcodeApi } from '@hospital/api';
import type { LowCodePage } from '@hospital/api';

/** 状态标签 */
const statusMap: Record<number, { text: string; color: string }> = {
  0: { text: '草稿', color: 'default' },
  1: { text: '已发布', color: 'success' },
  2: { text: '已归档', color: 'warning' },
};

/** 页面管理列表 */
const LowCodeList: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<LowCodePage>[] = [
    {
      title: '页面名称',
      dataIndex: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '标识',
      dataIndex: 'slug',
      width: 150,
      ellipsis: true,
      copyable: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      width: 200,
      ellipsis: true,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        0: { text: '草稿', status: 'Default' },
        1: { text: '已发布', status: 'Success' },
        2: { text: '已归档', status: 'Warning' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 180,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      width: 180,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      search: false,
      render: (_, record) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              history.push(`/platform/lowcode/editor/${record.id}`);
            }}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              window.open(`/platform/lowcode/preview/${record.id}`, '_blank');
            }}
          >
            预览
          </Button>
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={async () => {
              try {
                message.loading({ content: '正在复制...', key: 'copy' });
                const detail = await lowcodeApi.getPage(record.id);
                const newPage = await lowcodeApi.createPage({
                  name: `${record.name} 副本`,
                  slug: `${record.slug}-copy`,
                  description: detail.description,
                  schemaData: detail.schemaData,
                });
                message.success({ content: '复制成功', key: 'copy' });
                history.push(`/platform/lowcode/editor/${newPage.id}`);
              } catch {
                message.error({ content: '复制失败', key: 'copy' });
              }
            }}
          >
            复制
          </Button>
          {record.status === 0 && (
            <Button
              type="link"
              size="small"
              icon={<SendOutlined />}
              onClick={async () => {
                try {
                  await lowcodeApi.publishPage(record.id);
                  message.success('发布成功');
                  actionRef.current?.reload();
                } catch {
                  message.error('发布失败');
                }
              }}
            >
              发布
            </Button>
          )}
          {record.status === 0 && (
            <Popconfirm
              title="确定删除该页面？"
              onConfirm={async () => {
                try {
                  await lowcodeApi.deletePage(record.id);
                  message.success('删除成功');
                  actionRef.current?.reload();
                } catch {
                  message.error('删除失败');
                }
              }}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const request = useCallback(async (params: any) => {
    const { current, pageSize, status, ...rest } = params;
    try {
      const result = await lowcodeApi.getPages({
        page: current,
        pageSize,
        status: status !== undefined ? Number(status) : undefined,
        keyword: rest.name,
      });
      return {
        data: result.data,
        total: result.total,
        success: true,
      };
    } catch {
      return { data: [], total: 0, success: false };
    }
  }, []);

  return (
    <PageContainer
      header={{ title: '页面管理' }}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => history.push('/platform/lowcode/editor/new')}
        >
          新建页面
        </Button>
      }
    >
      <ProTable<LowCodePage>
        actionRef={actionRef}
        columns={columns}
        request={request}
        rowKey="id"
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default LowCodeList;
