/** 审批流相关类型定义 */

/** 审批实例状态 */
export type ApprovalInstanceStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'withdrawn';

/** 审批任务状态 */
export type ApprovalTaskStatus = 'pending' | 'completed' | 'cancelled' | 'transferred' | 'expired';

/** 审批记录动作 */
export type ApprovalAction = 'approve' | 'reject' | 'delegate' | 'comment' | 'withdraw';

/** 审批记录 */
export interface ApprovalRecord {
  id: string;
  nodeKey: string;
  nodeName?: string;
  approverId: string;
  approverName?: string;
  action: ApprovalAction;
  comment?: string;
  delegateTo?: string;
  createdAt?: string;
}

/** 审批任务 */
export interface ApprovalTask {
  id: string;
  instanceId: string;
  nodeKey: string;
  nodeName?: string;
  taskType: 'approval' | 'cc';
  status: ApprovalTaskStatus;
  assigneeId: string;
  assigneeName?: string;
  candidateUserIds?: string[];
  assigneeSnapshot?: Record<string, any>;
  completedAt?: string;
  completedBy?: string;
  timeoutAt?: string;
  createdAt?: string;
}

/** 审批实例 */
export interface ApprovalInstance {
  id: string;
  flowDefId: string;
  businessType: string;
  businessId: string;
  title: string;
  formData: Record<string, any>;
  status: ApprovalInstanceStatus;
  currentNodeKey?: string;
  applicantId: string;
  applicantName?: string;
  approvedAt?: string;
  rejectedAt?: string;
  cancelledAt?: string;
  completedReason?: string;
  records: ApprovalRecord[];
  tasks?: ApprovalTask[];
  createdAt?: string;
}

/** 审批实例列表项 */
export interface ApprovalInstanceListItem {
  id: string;
  businessType: string;
  businessId: string;
  title: string;
  status: ApprovalInstanceStatus;
  applicantId: string;
  applicantName?: string;
  currentNodeKey?: string;
  createdAt?: string;
}

/** 审批查询参数 */
export interface ApprovalQueryParams {
  page?: number;
  pageSize?: number;
  status?: ApprovalInstanceStatus;
  businessType?: string;
  applicantId?: string;
  storeId?: string;
}

/** 审批进度 */
export interface ApprovalProgress {
  status: ApprovalInstanceStatus;
  currentNode?: string;
  approvalMode?: string;
  totalApprovers: number;
  approvedCount: number;
  approvers: Array<{
    id: string;
    name: string;
    approved: boolean;
  }>;
}

/** 流程节点 */
export interface FlowNode {
  id: string;
  nodeKey: string;
  nodeName: string;
  nodeType: 'start' | 'approval' | 'cc' | 'condition' | 'end';
  approvalMode?: 'and' | 'or' | 'sequential';
  assigneeType?: string;
  assigneeConfig?: Record<string, any>;
  timeoutHours?: number;
  timeoutAction?: 'remind' | 'auto_approve' | 'auto_reject' | 'transfer';
  sortOrder: number;
  positionX?: number;
  positionY?: number;
  conditions: FlowCondition[];
}

/** 流程条件 */
export interface FlowCondition {
  id: string;
  nodeId: string;
  targetNodeKey: string;
  fieldName: string;
  operator: string;
  value: string;
  priority: number;
}

/** 流程定义 */
export interface FlowDefinition {
  id: string;
  name: string;
  businessType: string;
  description?: string;
  version: number;
  status: 'draft' | 'active' | 'archived';
  formSchema?: Record<string, any>;
  callbackConfig?: Record<string, any>;
  storeId?: string;
  snapshotJson?: Record<string, any>;
  nodes: FlowNode[];
  createdAt?: string;
  updatedAt?: string;
}

/** 流程定义列表项 */
export interface FlowDefinitionListItem {
  id: string;
  name: string;
  businessType: string;
  version: number;
  status: 'draft' | 'active' | 'archived';
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}
