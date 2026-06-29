"""BPMN XML 解析器单元测试"""

import pytest

from app.modules.approval_flows.bpmn_parser import parse_bpmn_xml


# 用户提供的 Flowable BPMN XML 示例
SAMPLE_BPMN_XML = """\
<?xml version='1.0' encoding='UTF-8'?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xmlns:xsd="http://www.w3.org/2001/XMLSchema"
             xmlns:flowable="http://flowable.org/bpmn"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:omgdc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:omgdi="http://www.omg.org/spec/DD/20100524/DI"
             typeLanguage="http://www.w3.org/2001/XMLSchema"
             expressionLanguage="http://www.w3.org/1999/XPath"
             targetNamespace="http://flowable.org/test">
  <process id="personEntryExit2" name="供应商人员进退场审批" isExecutable="true">
    <startEvent id="startEvent1" flowable:initiator="applyUserId"/>
    <userTask id="Activity_1otipts" name="提交审批"
              flowable:candidateGroups="pm_anhuanbu_director,pm_anhuanbu_deputy_director"
              flowable:formKey="{&quot;b&quot;:&quot;/occsafety/personManage/employeeManage2/detail?type=edit&amp;id={businessKey}&quot;,&quot;m&quot;:&quot;/&quot;}"/>
    <exclusiveGateway id="Gateway_0evyocg" name="安环部主任/副主任审批"/>
    <sequenceFlow id="Flow_0vzpk3p" sourceRef="Activity_1otipts" targetRef="Gateway_0evyocg"/>
    <endEvent id="Event_0tbzze4"/>
    <sequenceFlow id="Flow_0hvpbhb" name="通过" sourceRef="Gateway_0evyocg" targetRef="Event_0tbzze4">
      <documentation>{param:{'pass':'true','flowName':'通过'},type:'0'}</documentation>
      <conditionExpression xsi:type="tFormalExpression"><![CDATA[${pass == 'true'}]]></conditionExpression>
    </sequenceFlow>
    <userTask id="Activity_05x2sta" name="操作人处理"
              flowable:assignee="${header}"
              flowable:formKey="{&quot;b&quot;:&quot;/occsafety/personManage/employeeManage2/detail?type=edit&amp;id={businessKey}&quot;,&quot;m&quot;:&quot;/&quot;}">
      <extensionElements>
        <modeler:initiator-can-complete xmlns:modeler="http://flowable.org/modeler"><![CDATA[false]]></modeler:initiator-can-complete>
      </extensionElements>
    </userTask>
    <sequenceFlow id="Flow_1cfefaw" sourceRef="Activity_05x2sta" targetRef="Activity_1otipts"/>
    <sequenceFlow id="Flow_1g4unjh" name="退回到操作人" sourceRef="Gateway_0evyocg" targetRef="Activity_05x2sta">
      <documentation>{param:{'pass':'flase','flowName':'退回到操作人'},type:'0'}</documentation>
      <conditionExpression xsi:type="tFormalExpression"><![CDATA[${pass == 'false'}]]></conditionExpression>
    </sequenceFlow>
    <sequenceFlow id="Flow_1x5l4zf" sourceRef="startEvent1" targetRef="Activity_05x2sta"/>
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_personEntryExit2">
    <bpmndi:BPMNPlane bpmnElement="personEntryExit2" id="BPMNPlane_personEntryExit2">
      <bpmndi:BPMNShape bpmnElement="startEvent1" id="BPMNShape_startEvent1">
        <omgdc:Bounds height="30.0" width="30.0" x="345.0" y="245.0"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape bpmnElement="Activity_1otipts" id="BPMNShape_Activity_1otipts">
        <omgdc:Bounds height="80.0" width="100.0" x="590.0" y="220.0"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape bpmnElement="Gateway_0evyocg" id="BPMNShape_Gateway_0evyocg">
        <omgdc:Bounds height="50.0" width="50.0" x="755.0" y="235.0"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape bpmnElement="Event_0tbzze4" id="BPMNShape_Event_0tbzze4">
        <omgdc:Bounds height="36.0" width="36.0" x="872.0" y="242.0"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape bpmnElement="Activity_05x2sta" id="BPMNShape_Activity_05x2sta">
        <omgdc:Bounds height="80.0" width="100.0" x="430.0" y="220.0"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge bpmnElement="Flow_0vzpk3p" id="BPMNEdge_Flow_0vzpk3p">
        <omgdi:waypoint x="689.9499999999999" y="260.0"/>
        <omgdi:waypoint x="755.0" y="260.0"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge bpmnElement="Flow_0hvpbhb" id="BPMNEdge_Flow_0hvpbhb">
        <omgdi:waypoint x="804.9386693914622" y="260.0"/>
        <omgdi:waypoint x="872.0" y="260.0"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge bpmnElement="Flow_1x5l4zf" id="BPMNEdge_Flow_1x5l4zf">
        <omgdi:waypoint x="374.94999873104683" y="260.0"/>
        <omgdi:waypoint x="430.0" y="260.0"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge bpmnElement="Flow_1cfefaw" id="BPMNEdge_Flow_1cfefaw">
        <omgdi:waypoint x="529.9499999998419" y="260.0"/>
        <omgdi:waypoint x="589.9999999999518" y="260.0"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge bpmnElement="Flow_1g4unjh" id="BPMNEdge_Flow_1g4unjh">
        <omgdi:waypoint x="780.0" y="235.0"/>
        <omgdi:waypoint x="780.0" y="110.0"/>
        <omgdi:waypoint x="480.0" y="110.0"/>
        <omgdi:waypoint x="480.0" y="220.0"/>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>
"""


class TestBpmnParser:
    """BPMN 解析器测试"""

    def test_parse_basic_structure(self):
        """测试基本结构解析"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)

        assert result["name"] == "供应商人员进退场审批"
        assert result["business_type"] == "custom"
        assert "nodes" in result
        assert "edges" in result

    def test_parse_node_count(self):
        """测试节点数量"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes = result["nodes"]

        # 1 startEvent + 2 userTask + 1 exclusiveGateway + 1 endEvent = 5
        assert len(nodes) == 5

    def test_parse_node_types(self):
        """测试节点类型映射"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        assert nodes_by_key["startEvent1"]["nodeType"] == "start"
        assert nodes_by_key["Activity_1otipts"]["nodeType"] == "approval"
        assert nodes_by_key["Activity_05x2sta"]["nodeType"] == "approval"
        assert nodes_by_key["Gateway_0evyocg"]["nodeType"] == "condition"
        assert nodes_by_key["Event_0tbzze4"]["nodeType"] == "end"

    def test_parse_node_names(self):
        """测试节点名称"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        assert nodes_by_key["startEvent1"]["nodeName"] == "startEvent1"  # 无 name 属性，回退到 id
        assert nodes_by_key["Activity_1otipts"]["nodeName"] == "提交审批"
        assert nodes_by_key["Activity_05x2sta"]["nodeName"] == "操作人处理"
        assert nodes_by_key["Gateway_0evyocg"]["nodeName"] == "安环部主任/副主任审批"
        assert nodes_by_key["Event_0tbzze4"]["nodeName"] == "Event_0tbzze4"  # 无 name 属性

    def test_parse_candidate_groups(self):
        """测试 candidateGroups → assignee_type=role"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        node = nodes_by_key["Activity_1otipts"]
        assert node["assigneeType"] == "role"
        assert node["assigneeConfig"]["role_codes"] == ["pm_anhuanbu_director", "pm_anhuanbu_deputy_director"]
        assert node["assigneeConfig"]["same_store"] is True

    def test_parse_assignee_dynamic(self):
        """测试 assignee → assignee_type=dynamic"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        node = nodes_by_key["Activity_05x2sta"]
        assert node["assigneeType"] == "dynamic"
        assert node["assigneeConfig"]["field_name"] == "header"

    def test_parse_condition_gateway(self):
        """测试 exclusiveGateway → condition 节点的条件规则"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        gateway = nodes_by_key["Gateway_0evyocg"]
        assert gateway["nodeType"] == "condition"
        assert "conditions" in gateway

        conditions = gateway["conditions"]
        # 应该有 2 个条件: pass == 'true' 和 pass == 'false'
        assert len(conditions) == 2

        # 检查条件字段
        condition_targets = {c["targetNodeKey"]: c for c in conditions}
        assert "Event_0tbzze4" in condition_targets
        assert "Activity_05x2sta" in condition_targets

        # 通过条件
        pass_true = condition_targets["Event_0tbzze4"]
        assert pass_true["fieldName"] == "pass"
        assert pass_true["operator"] == "eq"
        assert pass_true["value"] == "true"

        # 退回条件
        pass_false = condition_targets["Activity_05x2sta"]
        assert pass_false["fieldName"] == "pass"
        assert pass_false["operator"] == "eq"
        assert pass_false["value"] == "false"

    def test_parse_edges(self):
        """测试边的数量和结构"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        edges = result["edges"]

        # 至少应有边存在
        assert len(edges) > 0

        # 检查边的 source/target 格式
        for edge in edges:
            assert "source" in edge
            assert "target" in edge

    def test_parse_positions(self):
        """测试 BPMNDI 坐标解析"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        # startEvent1 在 x=345, y=245
        assert nodes_by_key["startEvent1"]["positionX"] == 345.0
        assert nodes_by_key["startEvent1"]["positionY"] == 245.0

        # Activity_1otipts 在 x=590, y=220
        assert nodes_by_key["Activity_1otipts"]["positionX"] == 590.0
        assert nodes_by_key["Activity_1otipts"]["positionY"] == 220.0

    def test_parse_approval_mode_default(self):
        """测试 approval 节点默认审批模式为 or"""
        result = parse_bpmn_xml(SAMPLE_BPMN_XML)
        nodes_by_key = {n["nodeKey"]: n for n in result["nodes"]}

        assert nodes_by_key["Activity_1otipts"]["approvalMode"] == "or"
        assert nodes_by_key["Activity_05x2sta"]["approvalMode"] == "or"

    def test_parse_minimal_bpmn(self):
        """测试最简 BPMN（仅 start + end）"""
        minimal_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <process id="simple" name="简单流程">
    <startEvent id="start"/>
    <endEvent id="end"/>
    <sequenceFlow id="flow1" sourceRef="start" targetRef="end"/>
  </process>
</definitions>"""
        result = parse_bpmn_xml(minimal_xml)

        assert result["name"] == "简单流程"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    def test_parse_invalid_xml_raises(self):
        """测试无效 XML 抛出异常"""
        with pytest.raises(Exception):
            parse_bpmn_xml("not xml")

    def test_parse_no_process_raises(self):
        """测试缺少 process 元素抛出异常"""
        xml = '<?xml version="1.0"?><definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"></definitions>'
        with pytest.raises(ValueError, match="未找到"):
            parse_bpmn_xml(xml)

    def test_parse_condition_expression_formats(self):
        """测试不同条件表达式格式"""
        from app.modules.approval_flows.bpmn_parser import _parse_condition_expression

        # 基本格式
        assert _parse_condition_expression("${pass == 'true'}") == ("pass", "eq", "true")
        assert _parse_condition_expression("${amount > 1000}") == ("amount", "gt", "1000")
        assert _parse_condition_expression("${status != 'rejected'}") == ("status", "neq", "rejected")
        assert _parse_condition_expression("${count >= 10}") == ("count", "gte", "10")
        assert _parse_condition_expression("${score < 60}") == ("score", "lt", "60")
        assert _parse_condition_expression("${level <= 3}") == ("level", "lte", "3")

        # 无空格格式
        assert _parse_condition_expression("${pass=='true'}") == ("pass", "eq", "true")

        # 无效格式返回 None
        assert _parse_condition_expression("invalid") is None
        assert _parse_condition_expression("") is None
