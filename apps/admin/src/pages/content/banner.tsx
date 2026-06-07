import { useMemo, useState, useCallback } from 'react';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Image, App } from 'antd';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { contentApi } from '@hospital/api';
import { useListPage } from '@/hooks/useListPage';
import { useDict } from '@/hooks/useDict';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import { DragHandle, SortableRow } from '@/components/SortableTable/SortableRow';
import type { Banner } from '@hospital/api';

const BannerPage: React.FC = () => {
  const { message } = App.useApp();
  const { actionRef, handleDelete } = useListPage({
    deleteFn: contentApi.deleteBanner,
  });
  const { options: positionOptions } = useDict('banner_position');
  const { options: linkTypeOptions } = useDict('banner_link_type');
  const positionEnum = useMemo(
    () => Object.fromEntries(positionOptions.map((o) => [o.value, o.label])),
    [positionOptions]
  );
  const linkTypeEnum = useMemo(
    () => Object.fromEntries(linkTypeOptions.map((o) => [Number(o.value), o.label])),
    [linkTypeOptions]
  );

  const [dataSource, setDataSource] = useState<Banner[]>([]);
  const [loading, setLoading] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = dataSource.findIndex((item) => item.id === active.id);
      const newIndex = dataSource.findIndex((item) => item.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const newItems = arrayMove(dataSource, oldIndex, newIndex);
      setDataSource(newItems);

      try {
        const sortItems = newItems.map((item, index) => ({
          id: item.id,
          sortOrder: index,
        }));
        await contentApi.updateBannerSort(sortItems);
        message.success('排序已更新');
      } catch {
        message.error('排序更新失败');
        setDataSource(dataSource);
      }
    },
    [dataSource, message]
  );

  const columns: ProColumns<Banner>[] = [
    {
      title: '',
      width: 50,
      search: false,
      render: () => <DragHandle />,
    },
    { title: '图片', dataIndex: 'imageUrl', width: 120, search: false, render: (_, r) => <Image src={r.imageUrl} width={100} /> },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '位置', dataIndex: 'position', width: 100, valueEnum: positionEnum },
    { title: '链接类型', dataIndex: 'linkType', width: 100, search: false, valueEnum: linkTypeEnum },
    { title: '排序', dataIndex: 'sortOrder', width: 70, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } } },
    createOperationColumn<Banner>({
      width: 120,
      editUrl: (r) => `/content-center/content/banner/${r.id}/edit`,
      editPermission: 'content:banner:update',
      onDelete: handleDelete,
      deletePermission: 'content:banner:delete',
      deleteConfirmText: '确定删除吗？',
    }),
  ];

  return (
    <PageContainer>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={dataSource.map((item) => item.id)} strategy={verticalListSortingStrategy}>
          <ProTable<Banner>
            headerTitle="轮播图列表"
            actionRef={actionRef}
            rowKey="id"
            columns={columns}
            loading={loading}
            dataSource={dataSource}
            request={async (params) => {
              setLoading(true);
              try {
                const result = await contentApi.getBannerList({
                  ...params,
                  page: params.current,
                  pageSize: params.pageSize,
                });
                setDataSource(result.data || []);
                return {
                  data: result.data || [],
                  total: result.total || 0,
                  success: true,
                };
              } finally {
                setLoading(false);
              }
            }}
            components={{
              body: {
                row: SortableRow,
              },
            }}
            onRow={(record) => ({
              'data-row-key': record.id,
            } as any)}
            toolBarRender={() => [
              <CreateButton
                key="add"
                permission="content:banner:create"
                url="/content-center/content/banner/create"
                label="新增轮播图"
              />,
            ]}
            pagination={{ defaultPageSize: 10 }}
          />
        </SortableContext>
      </DndContext>
    </PageContainer>
  );
};

export default BannerPage;
