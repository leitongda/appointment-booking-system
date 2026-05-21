import React from 'react';
import { useDraggable } from '@dnd-kit/core';
import { HolderOutlined } from '@ant-design/icons';
import type { Schedule, Appointment } from '@hospital/shared';
import TimeSlotCell from './TimeSlotCell';

interface DraggableScheduleCellProps {
  schedule: Schedule;
  appointments: Appointment[];
  onAppointmentClick?: (appointment: Appointment) => void;
  onCreateClick?: (scheduleId: string) => void;
  isOverridden?: boolean;
}

/** 判断排班是否可拖拽（无预约、非停诊、非历史覆盖） */
export const isScheduleDraggable = (schedule: Schedule, overridden?: boolean): boolean => {
  if (overridden) return false;
  if (schedule.status === 0) return false; // 停诊
  // 可以拖拽: 有预约的也可以拖（整组移动），无预约的更可以拖
  return true;
};

const DraggableScheduleCell: React.FC<DraggableScheduleCellProps> = ({
  schedule,
  appointments,
  onAppointmentClick,
  onCreateClick,
  isOverridden,
}) => {
  const draggableId = `draggable-${schedule.id}`;
  const canDrag = isScheduleDraggable(schedule, isOverridden);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  } = useDraggable({
    id: draggableId,
    disabled: !canDrag,
    data: {
      schedule,
    },
  });

  const style: React.CSSProperties = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
      }
    : {};

  return (
    <div
      ref={setNodeRef}
      className={`draggable-schedule-cell ${isDragging ? 'dragging' : ''} ${canDrag ? 'can-drag' : ''}`}
      style={style}
    >
      {canDrag && (
        <div className="drag-handle" {...listeners} {...attributes}>
          <HolderOutlined />
        </div>
      )}
      <TimeSlotCell
        schedule={schedule}
        appointments={appointments}
        onAppointmentClick={onAppointmentClick}
        onCreateClick={onCreateClick}
        isOverridden={isOverridden}
      />
    </div>
  );
};

export default DraggableScheduleCell;
