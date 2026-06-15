/** 流程设计器 — 节点数据 */
export interface DesignerNodeData {
  label: string
  nodeType: 'start' | 'approval' | 'cc' | 'condition' | 'end'
  nodeKey: string
  approvalMode?: 'and' | 'or' | 'sequential'
  assigneeType?: 'role' | 'user' | 'department' | 'dynamic'
  assigneeConfig?: Record<string, any>
  timeoutHours?: number
  timeoutAction?: 'remind' | 'auto_approve' | 'auto_reject' | 'transfer'
  conditions?: FlowConditionData[]
}

export interface FlowConditionData {
  targetNodeKey: string
  fieldName: string
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'not_in' | 'contains' | 'exists'
  value: string
  priority: number
}

/** 流程校验结果 */
export interface FlowValidationResult {
  valid: boolean
  errors: string[]
}
