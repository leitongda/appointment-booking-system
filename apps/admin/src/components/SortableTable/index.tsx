import React, { useState, useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { Table, App } from 'antd';
import type { TableProps } from 'antd';
import { SortableRow } from './SortableRow';

export interface SortableTableProps<T> extends Omit<TableProps<T>, 'components' | 'onRow'> {
  /** 拖拽排序后的回调 */
  onSortEnd?: (items: T[], oldIndex: number, newIndex: number) => void | Promise<void>;
  /** 是否启用拖拽排序 */
  sortable?: boolean;
}

export function SortableTable<T extends { id: string }>({
  dataSource,
  sortable = true,
  onSortEnd,
  ...restProps
}: SortableTableProps<T>) {
  const { message } = App.useApp();
  const [sorting, setSorting] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;

      if (!over || active.id === over.id || !dataSource) {
        return;
      }

      const items = [...dataSource] as T[];
      const oldIndex = items.findIndex((item) => item.id === active.id);
      const newIndex = items.findIndex((item) => item.id === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        return;
      }

      const newItems = arrayMove(items, oldIndex, newIndex);

      if (onSortEnd) {
        setSorting(true);
        try {
          await onSortEnd(newItems, oldIndex, newIndex);
        } catch (error: any) {
          message.error(error.message || '排序失败');
        } finally {
          setSorting(false);
        }
      }
    },
    [dataSource, onSortEnd, message]
  );

  if (!sortable) {
    return <Table<T> dataSource={dataSource} {...restProps} />;
  }

  const items = (dataSource || []) as T[];

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis]}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={items.map((item) => item.id)} strategy={verticalListSortingStrategy}>
        <Table<T>
          dataSource={dataSource}
          loading={sorting || restProps.loading}
          {...restProps}
          components={{
            body: {
              row: SortableRow,
            },
          }}
          onRow={(record) => ({
            'data-row-key': record.id,
          } as any)}
        />
      </SortableContext>
    </DndContext>
  );
}

export { DragHandle } from './SortableRow';
export default SortableTable;

