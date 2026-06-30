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
          stroke: isDefault ? 'var(--color-border)' : 'var(--color-evening)',
          strokeWidth: isDefault ? 1 : 1.5,
          strokeDasharray: isDefault ? '6,4' : undefined,
          transition: 'stroke 0.15s ease, stroke-width 0.15s ease',
        }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className={`rf-edge-label ${isDefault ? '' : 'rf-edge-label--active'}`}
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
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
