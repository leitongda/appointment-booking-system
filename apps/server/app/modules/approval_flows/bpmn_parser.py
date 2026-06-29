"""BPMN XML 解析器 — 将 Flowable BPMN XML 转换为内部审批流程定义格式

支持的 BPMN 元素:
- startEvent → start 节点
- userTask → approval 节点
- exclusiveGateway → condition 节点
- endEvent → end 节点
- sequenceFlow → edge + condition 规则

支持的 Flowable 扩展属性:
- flowable:candidateGroups → assignee_type="role"
- flowable:assignee → assignee_type="dynamic"
- flowable:formKey → 存储在节点 metadata 中
- flowable:initiator → 存储在流程 metadata 中
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# XML 命名空间
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
OMGDC_NS = "http://www.omg.org/spec/DD/20100524/DC"
FLOWABLE_NS = "http://flowable.org/bpmn"

# 注册命名空间以避免 ns0 前缀
NS_MAP = {
    "bpmn": BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "omgdc": OMGDC_NS,
    "flowable": FLOWABLE_NS,
}

# BPMN 元素 → 内部 node_type 映射
ELEMENT_TYPE_MAP = {
    "startEvent": "start",
    "userTask": "approval",
    "serviceTask": "approval",
    "sendTask": "approval",
    "receiveTask": "approval",
    "scriptTask": "approval",
    "manualTask": "approval",
    "businessRuleTask": "approval",
    "exclusiveGateway": "condition",
    "inclusiveGateway": "condition",
    "parallelGateway": "condition",
    "endEvent": "end",
}

# 条件表达式解析: ${pass == 'true'} / ${amount > 1000} 等
_CONDITION_PATTERN = re.compile(
    r"\$\{\s*(\w+)\s*(==|!=|>=|<=|>|<|contains|in)\s*['\"]?([^'\"}\s]+)['\"]?\s*\}"
)


@dataclass
class BpmnElement:
    """BPMN 元素中间表示"""

    id: str
    name: str
    element_type: str  # BPMN 标签名 (startEvent, userTask, etc.)
    node_type: str  # 内部类型 (start, approval, condition, end)
    candidate_groups: str | None = None
    assignee: str | None = None
    form_key: str | None = None
    initiator: str | None = None
    position_x: float = 0.0
    position_y: float = 0.0


@dataclass
class BpmnSequenceFlow:
    """BPMN 连线中间表示"""

    id: str
    name: str
    source_ref: str
    target_ref: str
    condition_expression: str | None = None


def parse_bpmn_xml(xml_content: str | bytes) -> dict:
    """解析 BPMN XML，返回 FlowDefinitionCreate 兼容的 dict

    返回格式:
    {
        "name": str,
        "business_type": "custom",
        "nodes": [...],
        "edges": [...],
    }
    """
    root = ET.fromstring(xml_content)

    # 提取命名空间前缀（处理不同工具导出的命名空间差异）
    _detect_namespaces(root)

    # 找到 <process> 元素
    process = root.find(f"{{{BPMN_NS}}}process")
    if process is None:
        raise ValueError("BPMN XML 中未找到 <process> 元素")

    process_name = str(process.get("name") or "未命名流程")
    process_id = str(process.get("id") or "process_1")

    # 解析所有元素
    elements: dict[str, BpmnElement] = {}
    flows: list[BpmnSequenceFlow] = []

    for child in process:
        tag = _local_name(child.tag)

        if tag in ELEMENT_TYPE_MAP:
            elem = _parse_element(child, tag)
            elements[elem.id] = elem

        elif tag == "sequenceFlow":
            flow = _parse_sequence_flow(child)
            flows.append(flow)

    # 解析 BPMNDI 获取坐标
    _parse_positions(root, elements)

    # 构建内部格式
    nodes, edges = _build_internal_format(elements, flows)

    return {
        "name": process_name,
        "business_type": "custom",
        "description": f"从 BPMN 导入 (process_id: {process_id})",
        "nodes": nodes,
        "edges": edges,
    }


def _detect_namespaces(root: ET.Element) -> None:
    """检测并更新命名空间映射（处理不同 BPMN 工具的命名空间差异）

    ElementTree 将 xmlns:prefix="uri" 声明解析为 {uri} 格式的属性名。
    仅匹配确切的命名空间 URI 片段，避免误匹配 targetNamespace 等属性值。
    """
    global BPMN_NS, BPMNDI_NS, OMGDC_NS, FLOWABLE_NS

    for attr in root.attrib:
        if not attr.startswith("{"):
            continue
        uri = attr[1:-1]  # 去掉 { }
        if "BPMN/20100524/MODEL" in uri:
            BPMN_NS = uri
        elif "BPMN/20100524/DI" in uri:
            BPMNDI_NS = uri
        elif "DD/20100524/DC" in uri:
            OMGDC_NS = uri
        elif "flowable.org/bpmn" in uri:
            FLOWABLE_NS = uri


def _local_name(tag: str) -> str:
    """提取标签的本地名（去掉命名空间）"""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_element(elem: ET.Element, tag: str) -> BpmnElement:
    """解析单个 BPMN 元素"""
    elem_id = str(elem.get("id") or "")
    elem_name = str(elem.get("name") or "")
    node_type = ELEMENT_TYPE_MAP.get(tag, "approval")

    # 提取 Flowable 扩展属性
    candidate_groups = elem.get(f"{{{FLOWABLE_NS}}}candidateGroups")
    assignee = elem.get(f"{{{FLOWABLE_NS}}}assignee")
    form_key = elem.get(f"{{{FLOWABLE_NS}}}formKey")
    initiator = elem.get(f"{{{FLOWABLE_NS}}}initiator")

    # 如果 name 为空，使用 id 作为默认名
    if not elem_name:
        elem_name = elem_id

    return BpmnElement(
        id=elem_id,
        name=elem_name,
        element_type=tag,
        node_type=node_type,
        candidate_groups=candidate_groups,
        assignee=assignee,
        form_key=form_key,
        initiator=initiator,
    )


def _parse_sequence_flow(flow: ET.Element) -> BpmnSequenceFlow:
    """解析 sequenceFlow 元素"""
    flow_id = flow.get("id", "")
    flow_name = flow.get("name", "")
    source_ref = flow.get("sourceRef", "")
    target_ref = flow.get("targetRef", "")

    # 提取条件表达式
    condition_expr = None
    condition_elem = flow.find(f"{{{BPMN_NS}}}conditionExpression")
    if condition_elem is not None and condition_elem.text:
        condition_expr = condition_elem.text.strip()

    return BpmnSequenceFlow(
        id=flow_id,
        name=flow_name,
        source_ref=source_ref,
        target_ref=target_ref,
        condition_expression=condition_expr,
    )


def _parse_positions(root: ET.Element, elements: dict[str, BpmnElement]) -> None:
    """从 BPMNDI 解析元素坐标"""
    diagram = root.find(f".//{{{BPMNDI_NS}}}BPMNDiagram")
    if diagram is None:
        return

    plane = diagram.find(f"{{{BPMNDI_NS}}}BPMNPlane")
    if plane is None:
        return

    for shape in plane.findall(f"{{{BPMNDI_NS}}}BPMNShape"):
        bpmn_elem_ref = shape.get("bpmnElement", "")
        if bpmn_elem_ref in elements:
            bounds = shape.find(f"{{{OMGDC_NS}}}Bounds")
            if bounds is not None:
                elements[bpmn_elem_ref].position_x = float(bounds.get("x", 0))
                elements[bpmn_elem_ref].position_y = float(bounds.get("y", 0))


def _build_internal_format(
    elements: dict[str, BpmnElement], flows: list[BpmnSequenceFlow]
) -> tuple[list[dict], list[dict]]:
    """将中间表示转换为内部节点和边格式"""
    nodes: list[dict] = []
    edges: list[dict] = []
    sort_order = 0

    # 构建 source → [flows] 和 target → [flows] 索引
    source_flows: dict[str, list[BpmnSequenceFlow]] = {}
    target_flows: dict[str, list[BpmnSequenceFlow]] = {}
    for flow in flows:
        source_flows.setdefault(flow.source_ref, []).append(flow)
        target_flows.setdefault(flow.target_ref, []).append(flow)

    # 识别需要拆分的 gateway（同时是汇聚和发散的）
    gateways_to_split: set[str] = set()
    for eid, elem in elements.items():
        if elem.element_type in ("exclusiveGateway", "inclusiveGateway", "parallelGateway"):
            in_count = len(target_flows.get(eid, []))
            out_count = len(source_flows.get(eid, []))
            if in_count > 1 and out_count > 1:
                gateways_to_split.add(eid)

    # 处理每个元素
    for eid, elem in elements.items():
        if elem.element_type in ("exclusiveGateway", "inclusiveGateway", "parallelGateway"):
            out_flows = source_flows.get(eid, [])
            has_conditions = any(f.condition_expression for f in out_flows)

            if has_conditions:
                # 作为 condition 节点
                conditions = _build_conditions(out_flows)
                node = _make_node(elem, sort_order, conditions=conditions)
                nodes.append(node)

                # 默认分支的边（无条件表达式的出边）
                for flow in out_flows:
                    if not flow.condition_expression:
                        edges.append({
                            "source": eid,
                            "target": flow.target_ref,
                            "sourceHandle": "default",
                            "targetHandle": "input",
                        })
            else:
                # 无条件分支的 gateway → 转为 approval 节点（占位）
                node = _make_node(elem, sort_order, node_type_override="approval")
                nodes.append(node)

                # 添加所有出边
                for flow in out_flows:
                    edges.append({
                        "source": eid,
                        "target": flow.target_ref,
                    })

        else:
            # 普通节点（start / userTask / end）
            node = _make_node(elem, sort_order)
            nodes.append(node)

            # 添加出边（非 condition 节点的出边直接添加）
            for flow in source_flows.get(eid, []):
                edge = {"source": eid, "target": flow.target_ref}
                edges.append(edge)

        sort_order += 1

    return nodes, edges


def _make_node(
    elem: BpmnElement,
    sort_order: int,
    conditions: list[dict] | None = None,
    node_type_override: str | None = None,
) -> dict:
    """构建内部节点 dict"""
    node_type = node_type_override or elem.node_type
    node: dict = {
        "nodeKey": elem.id,
        "nodeName": elem.name,
        "nodeType": node_type,
        "sortOrder": sort_order,
        "positionX": elem.position_x,
        "positionY": elem.position_y,
    }

    # approval 节点特有字段
    if node_type == "approval":
        node["approvalMode"] = "or"  # 默认或签
        assignee_type, assignee_config = _resolve_assignee(elem)
        if assignee_type:
            node["assigneeType"] = assignee_type
        if assignee_config:
            node["assigneeConfig"] = assignee_config

    # condition 节点特有字段
    if node_type == "condition" and conditions:
        node["conditions"] = conditions

    return node


def _resolve_assignee(elem: BpmnElement) -> tuple[str | None, dict | None]:
    """从 Flowable 属性解析审批人配置"""
    if elem.candidate_groups:
        # candidateGroups → assignee_type="role"
        groups = [g.strip() for g in elem.candidate_groups.split(",") if g.strip()]
        return "role", {"role_codes": groups, "same_store": True}

    if elem.assignee:
        # assignee="${header}" → assignee_type="dynamic"
        # 提取变量名: ${header} → header
        match = re.match(r"\$\{(\w+)\}", elem.assignee)
        if match:
            field_name = match.group(1)
            return "dynamic", {"field_name": field_name, "name_field": f"{field_name}_name"}
        # 如果是固定值，作为 user 模式
        return "user", {"user_ids": [elem.assignee]}

    return None, None


def _build_conditions(out_flows: list[BpmnSequenceFlow]) -> list[dict]:
    """从 exclusiveGateway 的出边构建条件规则"""
    conditions = []
    priority = 0

    for flow in out_flows:
        if not flow.condition_expression:
            # 无条件 = 默认分支，不在 conditions 中体现（通过 edge sourceHandle="default"）
            continue

        # 解析条件表达式
        parsed = _parse_condition_expression(flow.condition_expression)
        if parsed:
            field_name, operator, value = parsed
            conditions.append({
                "targetNodeKey": flow.target_ref,
                "fieldName": field_name,
                "operator": operator,
                "value": value,
                "priority": priority,
            })
            priority += 1

    return conditions


def _parse_condition_expression(expr: str) -> tuple[str, str, str] | None:
    """解析条件表达式

    支持格式:
    - ${pass == 'true'} → (pass, eq, true)
    - ${amount > 1000} → (amount, gt, 1000)
    - ${status != 'rejected'} → (status, neq, rejected)

    返回 (field_name, operator, value) 或 None
    """
    match = _CONDITION_PATTERN.match(expr)
    if not match:
        return None

    field_name = match.group(1)
    raw_op = match.group(2)
    value = match.group(3)

    # 映射操作符
    op_map = {
        "==": "eq",
        "!=": "neq",
        ">": "gt",
        ">=": "gte",
        "<": "lt",
        "<=": "lte",
        "contains": "contains",
        "in": "in",
    }
    operator = op_map.get(raw_op, "eq")

    return field_name, operator, value
