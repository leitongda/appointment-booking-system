#!/usr/bin/env python3
"""
从 FastAPI OpenAPI 规范生成 llms.txt 文件

llms.txt 是一个标准格式，帮助 LLM 更好地理解 API 结构和用法。
参考: https://llmstxt.org/

生成的文件包括：
- llms.txt / llms-full.txt: 完整 API 文档
- llms-domain-*.txt: 按业务域分类的文档
- llms-workflow-*.txt: 按业务流程分类的文档

使用方式:
    cd apps/server
    python scripts/generate_llms_txt.py
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Any

# 添加 app 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.core.config import settings


# =============================================================================
# 业务域映射配置
# =============================================================================
DOMAIN_MAPPING: dict[str, dict[str, Any]] = {
    "booking": {
        "name": "预约管理域",
        "desc": "预约、排班相关的核心功能，包括预约创建、排班管理、规则配置等",
        "tags": [
            "预约", "排班", "排班模板", "自定义排班", "停诊管理",
            "休息日设置", "规则管理", "班次类型", "医生预约设置", "复诊规则配置",
            "预约须知"
        ]
    },
    "user": {
        "name": "用户管理域",
        "desc": "用户认证、患者管理、就诊卡管理等用户相关功能",
        "tags": [
            "认证", "用户", "患者管理", "就诊卡管理", "黑名单管理", "用户收藏"
        ]
    },
    "medical": {
        "name": "医疗资源域",
        "desc": "医生、科室、门店等医疗资源的管理",
        "tags": [
            "医生", "科室", "门店管理", "诊费管理"
        ]
    },
    "service": {
        "name": "就诊服务域",
        "desc": "就诊相关服务，包括病历、医生端操作、停诊调班等",
        "tags": [
            "病历", "医生端", "停诊调班"
        ]
    },
    "system": {
        "name": "系统管理域",
        "desc": "系统级功能，包括权限管理、系统设置、数据导入导出等",
        "tags": [
            "权限管理", "系统设置", "审计日志", "数据导入导出", "数据导出", "文件上传"
        ]
    },
    "content": {
        "name": "内容通知域",
        "desc": "内容管理和消息通知相关功能",
        "tags": [
            "内容管理", "消息中心", "邮件模板", "用户反馈"
        ]
    },
    "analytics": {
        "name": "数据分析域",
        "desc": "数据统计和用户行为分析",
        "tags": [
            "数据统计", "用户行为分析"
        ]
    },
}


# =============================================================================
# 业务流程定义
# =============================================================================
WORKFLOW_DEFINITIONS: dict[str, dict[str, Any]] = {
    "appointment": {
        "name": "预约流程",
        "desc": "患者从查看医生到完成预约的完整流程",
        "steps": [
            {"step": 1, "name": "查看科室列表", "method": "GET", "path_pattern": "/departments/tree"},
            {"step": 2, "name": "查看科室下的医生", "method": "GET", "path_pattern": "/doctors/by-department/"},
            {"step": 3, "name": "查看医生详情", "method": "GET", "path_pattern": "/doctors/public/"},
            {"step": 4, "name": "获取可预约排班", "method": "GET", "path_pattern": "/schedules/available/"},
            {"step": 5, "name": "获取预约须知", "method": "GET", "path_pattern": "/booking-notices/public"},
            {"step": 6, "name": "检查重复预约", "method": "GET", "path_pattern": "/appointments/check-duplicate"},
            {"step": 7, "name": "创建预约", "method": "POST", "path_pattern": "/appointments", "exact": True},
            {"step": 8, "name": "查看预约详情", "method": "GET", "path_pattern": "/appointments/", "exclude": ["check", "today", "queue", "statistics", "by-no"]},
            {"step": 9, "name": "取消预约", "method": "PUT", "path_pattern": "/cancel"},
        ]
    },
    "checkin": {
        "name": "签到流程",
        "desc": "患者到达门店后的签到流程",
        "steps": [
            {"step": 1, "name": "获取门店签到二维码", "method": "GET", "path_pattern": "/stores/", "include": ["checkin-qrcode"]},
            {"step": 2, "name": "获取今日待签到预约", "method": "GET", "path_pattern": "/appointments/today-pending"},
            {"step": 3, "name": "按预约号查询", "method": "GET", "path_pattern": "/appointments/by-no/"},
            {"step": 4, "name": "签到", "method": "PUT", "path_pattern": "/sign-in"},
            {"step": 5, "name": "取消签到", "method": "PUT", "path_pattern": "/cancel-sign-in"},
            {"step": 6, "name": "查看签到队列", "method": "GET", "path_pattern": "/appointments/queue", "exact": True},
            {"step": 7, "name": "获取队列信息", "method": "GET", "path_pattern": "/queue/info"},
        ]
    },
    "calling": {
        "name": "叫号流程",
        "desc": "医生端的叫号和就诊管理流程",
        "steps": [
            {"step": 1, "name": "获取签到队列", "method": "GET", "path_pattern": "/doctor-portal/queue", "exact": True},
            {"step": 2, "name": "获取队列统计", "method": "GET", "path_pattern": "/doctor-portal/queue/info"},
            {"step": 3, "name": "叫号", "method": "PUT", "path_pattern": "/call"},
            {"step": 4, "name": "完成就诊", "method": "PUT", "path_pattern": "/complete"},
            {"step": 5, "name": "过号", "method": "PUT", "path_pattern": "/pass"},
            {"step": 6, "name": "重新叫号", "method": "PUT", "path_pattern": "/recall"},
            {"step": 7, "name": "标记爽约", "method": "PUT", "path_pattern": "/no-show"},
            {"step": 8, "name": "查看患者历史", "method": "GET", "path_pattern": "/doctor-portal/patients/"},
            {"step": 9, "name": "创建复诊预约", "method": "POST", "path_pattern": "/follow-up"},
        ]
    },
    "schedule": {
        "name": "排班管理流程",
        "desc": "管理员进行排班管理的完整流程",
        "steps": [
            {"step": 1, "name": "获取班次类型", "method": "GET", "path_pattern": "/shift-types"},
            {"step": 2, "name": "获取排班模板列表", "method": "GET", "path_pattern": "/schedule-templates", "exact": True},
            {"step": 3, "name": "创建排班模板", "method": "POST", "path_pattern": "/schedule-templates", "exact": True},
            {"step": 4, "name": "预览生成排班", "method": "POST", "path_pattern": "/preview-generate"},
            {"step": 5, "name": "生成排班", "method": "POST", "path_pattern": "/generate", "exclude": ["preview"]},
            {"step": 6, "name": "获取排班列表", "method": "GET", "path_pattern": "/schedules", "exact": True},
            {"step": 7, "name": "批量停诊", "method": "POST", "path_pattern": "/batch-suspend"},
            {"step": 8, "name": "批量恢复", "method": "POST", "path_pattern": "/batch-resume"},
            {"step": 9, "name": "添加休息日", "method": "POST", "path_pattern": "/rest-days", "exact": True},
            {"step": 10, "name": "创建停诊", "method": "POST", "path_pattern": "/schedule-suspensions", "exact": True},
        ]
    },
    "register": {
        "name": "患者注册流程",
        "desc": "新用户注册和添加就诊人的流程",
        "steps": [
            {"step": 1, "name": "微信登录", "method": "POST", "path_pattern": "/auth/wechat/login"},
            {"step": 2, "name": "获取微信手机号", "method": "POST", "path_pattern": "/auth/wechat/phone"},
            {"step": 3, "name": "绑定手机号", "method": "POST", "path_pattern": "/auth/wechat/bind-phone"},
            {"step": 4, "name": "绑定用户信息", "method": "POST", "path_pattern": "/auth/wechat/bind-userinfo"},
            {"step": 5, "name": "获取用户信息", "method": "GET", "path_pattern": "/users/profile"},
            {"step": 6, "name": "获取就诊人列表", "method": "GET", "path_pattern": "/users/patients", "exact": True},
            {"step": 7, "name": "添加就诊人", "method": "POST", "path_pattern": "/users/patients", "exact": True},
            {"step": 8, "name": "更新就诊人", "method": "PUT", "path_pattern": "/users/patients/"},
        ]
    },
}


def get_openapi_schema() -> dict[str, Any]:
    """获取 OpenAPI schema"""
    return app.openapi()


def group_endpoints_by_tag(paths: dict[str, Any]) -> dict[str, list[dict]]:
    """按 tag 分组端点"""
    endpoints_by_tag: dict[str, list[dict]] = defaultdict(list)
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                tags = details.get("tags", ["其他"])
                summary = details.get("summary", "")
                description = details.get("description", "")
                operation_id = details.get("operationId", "")
                parameters = details.get("parameters", [])
                request_body = details.get("requestBody", {})
                responses = details.get("responses", {})
                
                endpoint_info = {
                    "path": path,
                    "method": method.upper(),
                    "summary": summary,
                    "description": description,
                    "operation_id": operation_id,
                    "parameters": parameters,
                    "request_body": request_body,
                    "responses": responses,
                }
                
                for tag in tags:
                    endpoints_by_tag[tag].append(endpoint_info)
    
    return dict(endpoints_by_tag)


def format_parameter(param: dict) -> str:
    """格式化单个参数"""
    name = param.get("name", "")
    location = param.get("in", "")
    required = param.get("required", False)
    schema = param.get("schema", {})
    param_type = schema.get("type", "any")
    description = param.get("description", "")
    
    required_str = "必填" if required else "可选"
    desc_str = f" - {description}" if description else ""
    
    return f"  - `{name}` ({location}, {param_type}, {required_str}){desc_str}"


def format_request_body(request_body: dict, schemas: dict) -> str:
    """格式化请求体"""
    if not request_body:
        return ""
    
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})
    
    if not schema:
        return ""
    
    lines = ["  - **请求体**: application/json"]
    
    # 处理 $ref
    if "$ref" in schema:
        ref = schema["$ref"]
        schema_name = ref.split("/")[-1]
        lines.append(f"    - Schema: `{schema_name}`")
        
        # 尝试解析 schema 的属性
        if schema_name in schemas:
            props = schemas[schema_name].get("properties", {})
            required = schemas[schema_name].get("required", [])
            for prop_name, prop_info in list(props.items())[:5]:  # 限制显示前5个
                prop_type = prop_info.get("type", "any")
                req_str = "必填" if prop_name in required else "可选"
                lines.append(f"    - `{prop_name}` ({prop_type}, {req_str})")
            if len(props) > 5:
                lines.append(f"    - ... 还有 {len(props) - 5} 个字段")
    
    return "\n".join(lines)


def generate_llms_txt(schema: dict, endpoints_by_tag: dict[str, list[dict]]) -> str:
    """生成 llms.txt 概览版"""
    info = schema.get("info", {})
    title = info.get("title", "API")
    description = info.get("description", "")
    version = info.get("version", "1.0.0")
    
    lines = [
        f"# {title}",
        "",
        f"> {description}",
        "",
        f"- API 版本: {version}",
        f"- 基础路径: {settings.API_V1_STR}",
        f"- Swagger 文档: /docs",
        f"- ReDoc 文档: /redoc",
        f"- OpenAPI JSON: {settings.API_V1_STR}/openapi.json",
        "",
    ]
    
    # 按 tag 输出端点列表
    for tag, endpoints in endpoints_by_tag.items():
        lines.append(f"## {tag}")
        lines.append("")
        
        for ep in endpoints:
            method = ep["method"]
            path = ep["path"]
            # 优先使用中文 description，只取第一行
            desc = ep["description"] or ep["summary"] or ""
            if desc:
                desc = desc.split("\n")[0].strip()
            # 截断过长的描述
            if len(desc) > 60:
                desc = desc[:57] + "..."
            
            desc_part = f": {desc}" if desc else ""
            lines.append(f"- [{method} {path}]({path}){desc_part}")
        
        lines.append("")
    
    # Optional 部分
    lines.append("## Optional")
    lines.append("")
    lines.append(f"- [OpenAPI 规范 JSON]({settings.API_V1_STR}/openapi.json): 包含所有端点的完整定义，适合程序化处理")
    lines.append(f"- [llms-full.txt](/llms-full.txt): 包含所有端点详细参数信息的完整版本")
    lines.append("")
    
    return "\n".join(lines)


def generate_llms_full_txt(schema: dict, endpoints_by_tag: dict[str, list[dict]]) -> str:
    """生成 llms-full.txt 完整版"""
    info = schema.get("info", {})
    title = info.get("title", "API")
    description = info.get("description", "")
    version = info.get("version", "1.0.0")
    schemas = schema.get("components", {}).get("schemas", {})
    
    lines = [
        f"# {title}",
        "",
        f"> {description}",
        "",
        f"- API 版本: {version}",
        f"- 基础路径: {settings.API_V1_STR}",
        f"- 认证方式: Bearer Token (JWT)",
        "",
        "---",
        "",
    ]
    
    # 按 tag 输出详细端点信息
    for tag, endpoints in endpoints_by_tag.items():
        lines.append(f"## {tag}")
        lines.append("")
        
        for ep in endpoints:
            method = ep["method"]
            path = ep["path"]
            summary = ep["summary"] or ""
            description = ep["description"] or ""
            parameters = ep["parameters"]
            request_body = ep["request_body"]
            
            lines.append(f"### {method} {path}")
            lines.append("")
            
            if summary:
                lines.append(f"**{summary}**")
                lines.append("")
            
            if description and description != summary:
                lines.append(description)
                lines.append("")
            
            # 参数
            if parameters:
                lines.append("**参数:**")
                lines.append("")
                for param in parameters:
                    lines.append(format_parameter(param))
                lines.append("")
            
            # 请求体
            if request_body:
                body_str = format_request_body(request_body, schemas)
                if body_str:
                    lines.append("**请求:**")
                    lines.append("")
                    lines.append(body_str)
                    lines.append("")
            
            lines.append("---")
            lines.append("")
    
    return "\n".join(lines)


def generate_domain_file(
    domain_key: str,
    domain_config: dict,
    endpoints_by_tag: dict[str, list[dict]]
) -> str:
    """生成单个业务域的 llms.txt 文件"""
    name = domain_config["name"]
    desc = domain_config["desc"]
    tags = domain_config["tags"]
    
    lines = [
        f"# {name}",
        "",
        f"> {desc}",
        "",
        f"- 基础路径: {settings.API_V1_STR}",
        f"- 认证方式: Bearer Token (JWT)",
        "",
    ]
    
    # 统计端点数量
    total_endpoints = 0
    for tag in tags:
        if tag in endpoints_by_tag:
            total_endpoints += len(endpoints_by_tag[tag])
    
    lines.append(f"本域包含 {len(tags)} 个模块，共 {total_endpoints} 个端点。")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 按 tag 输出端点列表
    for tag in tags:
        if tag not in endpoints_by_tag:
            continue
        
        endpoints = endpoints_by_tag[tag]
        lines.append(f"## {tag}")
        lines.append("")
        
        for ep in endpoints:
            method = ep["method"]
            path = ep["path"]
            desc = ep["description"] or ep["summary"] or ""
            if desc:
                desc = desc.split("\n")[0].strip()
            if len(desc) > 60:
                desc = desc[:57] + "..."
            
            desc_part = f": {desc}" if desc else ""
            lines.append(f"- [{method} {path}]({path}){desc_part}")
        
        lines.append("")
    
    # 添加关联说明
    lines.append("## 相关文档")
    lines.append("")
    lines.append("- [完整 API 文档](/llms.txt): 所有 API 端点的概览")
    lines.append("- [详细 API 文档](/llms-full.txt): 包含参数详情的完整文档")
    lines.append("")
    
    return "\n".join(lines)


def generate_domain_files(
    endpoints_by_tag: dict[str, list[dict]],
    output_dir: Path
) -> list[str]:
    """生成所有业务域文件"""
    generated_files = []
    
    for domain_key, domain_config in DOMAIN_MAPPING.items():
        content = generate_domain_file(domain_key, domain_config, endpoints_by_tag)
        filename = f"llms-domain-{domain_key}.txt"
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        generated_files.append(filename)
        print(f"  ✅ {filename}")
    
    return generated_files


def match_endpoint_to_step(ep: dict, step: dict) -> bool:
    """检查端点是否匹配流程步骤"""
    method = ep["method"]
    path = ep["path"]
    
    # 检查 HTTP 方法
    if step["method"] != method:
        return False
    
    pattern = step["path_pattern"]
    
    # 精确匹配
    if step.get("exact"):
        # 对于精确匹配，路径必须以 /api/v1 + pattern 结尾
        expected_suffix = f"{settings.API_V1_STR}{pattern}"
        return path == expected_suffix or path.endswith(pattern)
    
    # 包含匹配
    if step.get("include"):
        for inc in step["include"]:
            if inc in path and pattern in path:
                return True
        return False
    
    # 排除匹配
    if step.get("exclude"):
        for exc in step["exclude"]:
            if exc in path:
                return False
    
    # 模糊匹配
    return pattern in path


def generate_workflow_file(
    workflow_key: str,
    workflow_config: dict,
    all_endpoints: list[dict]
) -> str:
    """生成单个业务流程的 llms.txt 文件"""
    name = workflow_config["name"]
    desc = workflow_config["desc"]
    steps = workflow_config["steps"]
    
    lines = [
        f"# {name}",
        "",
        f"> {desc}",
        "",
        f"- 基础路径: {settings.API_V1_STR}",
        f"- 认证方式: Bearer Token (JWT)",
        "",
        "---",
        "",
        "## 流程步骤",
        "",
    ]
    
    # 按步骤顺序匹配端点
    for step in steps:
        step_num = step["step"]
        step_name = step["name"]
        
        lines.append(f"### 步骤 {step_num}: {step_name}")
        lines.append("")
        
        # 查找匹配的端点
        matched_endpoints = []
        for ep in all_endpoints:
            if match_endpoint_to_step(ep, step):
                matched_endpoints.append(ep)
        
        if matched_endpoints:
            for ep in matched_endpoints:
                method = ep["method"]
                path = ep["path"]
                desc = ep["description"] or ep["summary"] or ""
                if desc:
                    desc = desc.split("\n")[0].strip()
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                
                desc_part = f": {desc}" if desc else ""
                lines.append(f"- [{method} {path}]({path}){desc_part}")
        else:
            lines.append(f"- *暂无匹配的端点*")
        
        lines.append("")
    
    # 添加关联说明
    lines.append("## 相关文档")
    lines.append("")
    lines.append("- [完整 API 文档](/llms.txt): 所有 API 端点的概览")
    lines.append("- [详细 API 文档](/llms-full.txt): 包含参数详情的完整文档")
    lines.append("")
    
    return "\n".join(lines)


def generate_workflow_files(
    endpoints_by_tag: dict[str, list[dict]],
    output_dir: Path
) -> list[str]:
    """生成所有业务流程文件"""
    # 将所有端点展平为一个列表
    all_endpoints = []
    for endpoints in endpoints_by_tag.values():
        all_endpoints.extend(endpoints)
    
    generated_files = []
    
    for workflow_key, workflow_config in WORKFLOW_DEFINITIONS.items():
        content = generate_workflow_file(workflow_key, workflow_config, all_endpoints)
        filename = f"llms-workflow-{workflow_key}.txt"
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        generated_files.append(filename)
        print(f"  ✅ {filename}")
    
    return generated_files


def main():
    """主函数"""
    # 获取 OpenAPI schema
    print("正在获取 OpenAPI schema...")
    schema = get_openapi_schema()
    
    # 按 tag 分组端点
    print("正在分析 API 端点...")
    paths = schema.get("paths", {})
    endpoints_by_tag = group_endpoints_by_tag(paths)
    
    total_endpoints = sum(len(eps) for eps in endpoints_by_tag.values())
    print(f"发现 {len(endpoints_by_tag)} 个分类，共 {total_endpoints} 个端点")
    
    # 生成文件
    output_dir = Path(__file__).parent.parent / "app" / "static"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 生成主文件 llms.txt
    print("\n📄 生成主文件...")
    llms_txt = generate_llms_txt(schema, endpoints_by_tag)
    llms_txt_path = output_dir / "llms.txt"
    llms_txt_path.write_text(llms_txt, encoding="utf-8")
    print(f"  ✅ llms.txt")
    
    # 2. 生成完整版 llms-full.txt
    llms_full_txt = generate_llms_full_txt(schema, endpoints_by_tag)
    llms_full_txt_path = output_dir / "llms-full.txt"
    llms_full_txt_path.write_text(llms_full_txt, encoding="utf-8")
    print(f"  ✅ llms-full.txt")
    
    # 3. 生成业务域文件
    print("\n📂 生成业务域文件...")
    domain_files = generate_domain_files(endpoints_by_tag, output_dir)
    
    # 4. 生成业务流程文件
    print("\n🔄 生成业务流程文件...")
    workflow_files = generate_workflow_files(endpoints_by_tag, output_dir)
    
    # 汇总
    total_files = 2 + len(domain_files) + len(workflow_files)
    print(f"\n✅ 完成！共生成 {total_files} 个文件")
    print("\n可通过以下端点访问：")
    print("  - GET /llms.txt (主文件)")
    print("  - GET /llms-full.txt (完整版)")
    print("  - GET /llms-domain-{domain}.txt (业务域文件)")
    print("  - GET /llms-workflow-{workflow}.txt (业务流程文件)")


if __name__ == "__main__":
    main()
