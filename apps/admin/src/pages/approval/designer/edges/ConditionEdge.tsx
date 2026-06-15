import { memo } from 'react';
import { getBezierPath, EdgeLabelRenderer, BaseEdge, type EdgeProps } from '@xyflow/react';

const ConditionEdge = memo(({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  data, style, markerEnd,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  });

  const label = data?.label as string;
  const isDefault = data?.isDefault as boolean;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: isDefault ? '#d9d9d9' : '#fa8c16',
          strokeWidth: isDefault ? 1 : 2,
          strokeDasharray: isDefault ? '5,5' : undefined,
        }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
              background: isDefault ? '#fafafa' : '#fff7e6',
              border: `1px solid ${isDefault ? '#d9d9d9' : '#fa8c16'}`,
              borderRadius: 4,
              padding: '2px 6px',
              fontSize: 11,
              color: isDefault ? '#999' : '#d46b08',
              whiteSpace: 'nowrap',
            }}
          >
            {isDefault ? '默认' : label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

ConditionEdge.displayName = 'ConditionEdge';
export default ConditionEdge;
