import React from 'react';
import { useDroppable } from '@dnd-kit/core';

interface DroppableTimeSlotProps {
  dateStr: string;
  timeSlot: string;
  children: React.ReactNode;
  className?: string;
}

const DroppableTimeSlot: React.FC<DroppableTimeSlotProps> = ({
  dateStr,
  timeSlot,
  children,
  className,
}) => {
  const droppableId = `droppable-${dateStr}-${timeSlot}`;

  const { isOver, setNodeRef } = useDroppable({
    id: droppableId,
    data: {
      date: dateStr,
      timeSlot,
    },
  });

  return (
    <div
      ref={setNodeRef}
      className={`droppable-time-slot ${isOver ? 'droppable-hover' : ''} ${className || ''}`}
    >
      {children}
    </div>
  );
};

export default DroppableTimeSlot;
