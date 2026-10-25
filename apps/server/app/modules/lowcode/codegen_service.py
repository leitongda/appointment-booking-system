"""低代码代码生成服务。

通过 subprocess 调用 Node.js codegen 包，将低代码 schema 转换为
Taro 小程序或原生小程序的可运行源代码。

环境变量:
    CODEGEN_BIN: Node.js codegen 入口脚本路径 (默认: <project>/packages/codegen/dist/index.js)
    CODEGEN_NODE_CMD: Node.js 可执行命令 (默认: node)
    CODEGEN_TIMEOUT: subprocess 超时秒数 (默认: 30)
"""

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 项目根目录 & 默认配置
# ---------------------------------------------------------------------------

def _resolve_project_root() -> Path:
    """monorepo 根目录。

    - 优先 CODEGEN_PROJECT_ROOT 环境变量；
    - 仓库布局（repo/apps/server/app/modules/lowcode/）按 packages/codegen
      标记逐级向上探测；
    - 容器内（/app/app/...，无 monorepo 上层）探测不到标记时回退到服务根，
      codegen 二进制不存在由运行期按缺 bin 报错，不再阻塞整个应用导入。
    """
    env_root = os.getenv("CODEGEN_PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "packages" / "codegen").exists():
            return parent
    return here.parents[3] if len(here.parents) > 3 else here.parent


_PROJECT_ROOT = _resolve_project_root()

_DEFAULT_CODEGEN_BIN = str(_PROJECT_ROOT / "packages" / "codegen" / "dist" / "index.js")
_DEFAULT_NODE_CMD = "node"
_DEFAULT_TIMEOUT = 30  # seconds


def _get_codegen_bin() -> str:
    return os.environ.get("CODEGEN_BIN", _DEFAULT_CODEGEN_BIN)


def _get_node_cmd() -> str:
    return os.environ.get("CODEGEN_NODE_CMD", _DEFAULT_NODE_CMD)


def _get_timeout() -> int:
    try:
        return int(os.environ.get("CODEGEN_TIMEOUT", _DEFAULT_TIMEOUT))
    except ValueError:
        return _DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# 数据类型
# ---------------------------------------------------------------------------


class GeneratedFileType(str, Enum):
    """生成文件的类型。"""

    TSX = "tsx"
    CSS = "css"
    JSON = "json"
    WXML = "wxml"
    WXSS = "wxss"
    JS = "js"


@dataclass
class GeneratedFile:
    """单个生成文件。"""

    path: str
    content: str
    type: GeneratedFileType

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "content": self.content,
            "type": self.type.value,
        }


@dataclass
class CodegenResult:
    """代码生成结果。"""

    files: list[GeneratedFile] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": [f.to_dict() for f in self.files],
            "warnings": self.warnings,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


class CodegenError(Exception):
    """代码生成异常。"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


# ---------------------------------------------------------------------------
# Node.js 脚本模板
# ---------------------------------------------------------------------------

# 薄包装脚本: 从 stdin 读取 JSON 输入，调用 codegen 包，输出 JSON 结果。
# 这样避免了 Python 拼接长 JS 字符串的转义问题。
_NODEJS_WRAPPER = """\
const fs = require('fs');

async function main() {{
    const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
    const schema = input.schema;
    const dataSources = input.dataSources || [];
    const state = input.state || {{}};
    const target = input.target || 'taro';
    const options = input.options || {{}};

    let result;

    if (target === 'taro') {{
        const codegen = require('{codegen_bin}');
        const pageCode = codegen.generatePage(schema, dataSources, state, options);
        const analysis = codegen.analyzeSchema
            ? codegen.analyzeSchema(schema)
            : {{ components: [], dataSources: [], dependencies: [], warnings: [] }};

        const pageName = schema.props?.navigationBarTitleText || 'page';
        const safeSlug = pageName.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase() || 'page';

        result = {{
            files: [
                {{
                    path: 'pages/' + safeSlug + '/index.tsx',
                    content: pageCode,
                    type: 'tsx',
                }},
            ],
            warnings: analysis.warnings || [],
            dependencies: extractDeps(pageCode),
            metadata: {{
                target: 'taro',
                components: analysis.components || [],
                dataSources: (analysis.dataSources || []).map(function(ds) {{ return ds.id; }}),
                generatedAt: new Date().toISOString(),
            }},
        }};
    }} else if (target === 'native') {{
        // Native (WeChat mini-program) output — 使用 codegen 包的完整生成器
        const codegen = require('{codegen_bin}');
        const slug = (schema.props?.navigationBarTitleText || 'page').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase() || 'page';
        const prefix = 'pages/' + slug;

        // 使用 codegen 包的 generateWxmlPage 生成完整 WXML（支持 dataBinding/loop/visible/事件）
        const wxml = codegen.generateWxmlPage(schema, {{ pageClass: 'page' }});
        const handlers = codegen.collectEventHandlers ? codegen.collectEventHandlers(schema) : [];
        const bindings = codegen.collectDataBindings ? codegen.collectDataBindings(schema) : new Set();

        // 生成 JS 逻辑（含事件处理函数）
        var jsLines = [];
        jsLines.push("Page({");
        jsLines.push("  data: {");
        jsLines.push("    loading: true,");
        var stateKeys = Object.keys(state);
        for (var i = 0; i < stateKeys.length; i++) {{
            var key = stateKeys[i];
            var val = state[key];
            var defaultVal = (val && val.defaultValue !== undefined) ? val.defaultValue : '';
            jsLines.push("    " + key + ": " + JSON.stringify(defaultVal) + ",");
        }}
        jsLines.push("  },");
        jsLines.push("  onLoad() {");
        for (var j = 0; j < dataSources.length; j++) {{
            var ds = dataSources[j];
            jsLines.push("    this.fetch_" + ds.id + "();");
        }}
        jsLines.push("    this.setData({ loading: false });");
        jsLines.push("  },");
        for (var k = 0; k < dataSources.length; k++) {{
            var ds2 = dataSources[k];
            jsLines.push("  fetch_" + ds2.id + "() {");
            jsLines.push("    wx.request({");
            jsLines.push("      url: '" + (ds2.url || '') + "',");
            jsLines.push("      method: '" + (ds2.method || 'GET') + "',");
            jsLines.push("      success: (res) => {");
            if (ds2.dataPath) {{
                jsLines.push("        this.setData({ " + ds2.id + ": res.data." + ds2.dataPath + " });");
            }} else {{
                jsLines.push("        this.setData({ " + ds2.id + ": res.data });");
            }}
            jsLines.push("      },");
            jsLines.push("      fail: (err) => {");
            jsLines.push("        console.error('Failed to fetch " + ds2.id + "', err);");
            jsLines.push("      }");
            jsLines.push("    });");
            jsLines.push("  },");
        }}
        // 事件处理函数（从 collectEventHandlers 获取）
        for (var h = 0; h < handlers.length; h++) {{
            var handler = handlers[h];
            jsLines.push("  " + handler.name + "(e) {");
            for (var a = 0; a < handler.actions.length; a++) {{
                var action = handler.actions[a];
                if (action.type === 'setData') {{
                    jsLines.push("    this.setData({ " + action.key + ": " + JSON.stringify(action.value) + " });");
                }} else if (action.type === 'navigate') {{
                    jsLines.push("    wx.navigateTo({ url: '" + action.url + "' });");
                }} else if (action.type === 'showToast') {{
                    jsLines.push("    wx.showToast({ title: '" + (action.title || '') + "', icon: 'none' });");
                }}
            }}
            jsLines.push("  },");
        }}
        jsLines.push("}});");
        var jsCode = jsLines.join('\\n');

        // WXSS: 复用现有样式
        var wxss = '.page {{\\n  min-height: 100vh;\\n  padding: 16rpx;\\n  box-sizing: border-box;\\n}}\\n';

        // JSON config
        var pageName = (schema.props && schema.props.navigationBarTitleText) || 'page';
        var config = {{
            navigationBarTitleText: pageName,
            usingComponents: {{}},
        }};

        result = {{
            files: [
                {{ path: prefix + '.wxml', content: wxml, type: 'wxml' }},
                {{ path: prefix + '.wxss', content: wxss, type: 'wxss' }},
                {{ path: prefix + '.js', content: jsCode, type: 'js' }},
                {{ path: prefix + '.json', content: JSON.stringify(config, null, 2), type: 'json' }},
            ],
            warnings: [],
            dependencies: ['wx'],
            metadata: {{
                target: 'native',
                generatedAt: new Date().toISOString(),
            }},
        }};
    }} else {{
        throw new Error('Unknown target: ' + target);
    }}

    process.stdout.write(JSON.stringify(result));
}}

function extractDeps(code) {{
    var deps = [];
    var re = /from\\s+['\"]([^'\"]+)['\"]/g;
    var m;
    while ((m = re.exec(code)) !== null) {{
        var dep = m[1];
        if (!dep.startsWith('.') && !dep.startsWith('/')) {{
            deps.push(dep);
        }}
    }}
    return deps;
}}

function generateNative(schema, dataSources, state, options) {{
    var pageName = (schema.props && schema.props.navigationBarTitleText) || 'page';
    var safeSlug = pageName.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase() || 'page';
    var prefix = 'pages/' + safeSlug;

    // WXML: convert component tree to WeChat WXML
    var wxml = '<view class="page">\\n' + generateWxml(schema.children || [], 1) + '</view>';

    // WXSS: basic page styles
    var wxss = '.page {{\\n  min-height: 100vh;\\n  padding: 16rpx;\\n  box-sizing: border-box;\\n}}\\n';

    // JS: page logic with data fetching
    var jsLines = [];
    jsLines.push("Page({");
    jsLines.push("  data: {");
    jsLines.push("    loading: true,");

    // State defaults
    var stateKeys = Object.keys(state);
    for (var i = 0; i < stateKeys.length; i++) {{
        var key = stateKeys[i];
        var val = state[key];
        var defaultVal = (val && val.defaultValue !== undefined) ? val.defaultValue : '';
        jsLines.push("    " + key + ": " + JSON.stringify(defaultVal) + ",");
    }}
    jsLines.push("  },");

    // onLoad with data fetching
    jsLines.push("  onLoad() {");
    for (var j = 0; j < dataSources.length; j++) {{
        var ds = dataSources[j];
        jsLines.push("    this.fetch_" + ds.id + "();");
    }}
    jsLines.push("    this.setData({ loading: false });");
    jsLines.push("  },");

    // Fetch functions
    for (var k = 0; k < dataSources.length; k++) {{
        var ds2 = dataSources[k];
        jsLines.push("  fetch_" + ds2.id + "() {");
        jsLines.push("    wx.request({");
        jsLines.push("      url: '" + (ds2.url || '') + "',");
        jsLines.push("      method: '" + (ds2.method || 'GET') + "',");
        jsLines.push("      success: (res) => {");
        if (ds2.dataPath) {{
            jsLines.push("        this.setData({ " + ds2.id + ": res.data." + ds2.dataPath + " });");
        }} else {{
            jsLines.push("        this.setData({ " + ds2.id + ": res.data });");
        }}
        jsLines.push("      },");
        jsLines.push("      fail: (err) => {");
        jsLines.push("        console.error('Failed to fetch " + ds2.id + "', err);");
        jsLines.push("      }");
        jsLines.push("    });");
        jsLines.push("  },");
    }}

    // Event handlers
    jsLines.push("  // Event handlers");
    jsLines.push("}});");

    var jsCode = jsLines.join('\\n');

    // JSON config
    var config = {{
        navigationBarTitleText: pageName,
        usingComponents: {{}},
    }};

    return {{
        files: [
            {{ path: prefix + '.wxml', content: wxml, type: 'wxml' }},
            {{ path: prefix + '.wxss', content: wxss, type: 'wxss' }},
            {{ path: prefix + '.js', content: jsCode, type: 'js' }},
            {{ path: prefix + '.json', content: JSON.stringify(config, null, 2), type: 'json' }},
        ],
        warnings: [],
        dependencies: ['wx'],
        metadata: {{
            target: 'native',
            generatedAt: new Date().toISOString(),
        }},
    }};
}}

function generateWxml(nodes, depth) {{
    var pad = '  '.repeat(depth);
    var lines = [];
    for (var i = 0; i < nodes.length; i++) {{
        var node = nodes[i];
        var tag = mapToWxmlTag(node.componentName);
        var attrs = buildWxmlAttrs(node);
        if (node.children && node.children.length > 0) {{
            lines.push(pad + '<' + tag + attrs + '>');
            lines.push(generateWxml(node.children, depth + 1));
            lines.push(pad + '</' + tag + '>');
        }} else {{
            var text = extractWxmlText(node);
            if (text !== null) {{
                lines.push(pad + '<' + tag + attrs + '>' + text + '</' + tag + '>');
            }} else {{
                lines.push(pad + '<' + tag + attrs + ' />');
            }}
        }}
    }}
    return lines.join('\\n');
}}

function mapToWxmlTag(name) {{
    var map = {{
        NutView: 'view', NutText: 'text', NutImage: 'image',
        NutButton: 'button', NutInput: 'input', NutTextarea: 'textarea',
        NutCell: 'view', NutCard: 'view', NutRow: 'view', NutCol: 'view',
        NutDivider: 'view', NutSwiper: 'swiper', NutSwiperItem: 'swiper-item',
        NutEmpty: 'view', NutForm: 'form', NutSwitch: 'switch',
        NutTabs: 'view', NutTabPane: 'view', NutPicker: 'picker',
        NutSearchBar: 'input', NutNavBar: 'view', NutIcon: 'text',
        NutTag: 'view', NutAvatar: 'image', NutBadge: 'view',
        NutProgress: 'progress', NutCheckbox: 'checkbox', NutRadio: 'radio',
        NutDatePicker: 'picker', NutCalendar: 'view',
    }};
    return map[name] || 'view';
}}

function buildWxmlAttrs(node) {{
    var parts = [];
    var props = node.props || {{}};
    if (props.className) parts.push('class="' + props.className + '"');
    if (props.src) parts.push('src="' + props.src + '"');
    if (props.placeholder) parts.push('placeholder="' + props.placeholder + '"');
    if (node.visible) parts.push('wx:if="{{' + node.visible + '}}"');
    return parts.length > 0 ? ' ' + parts.join(' ') : '';
}}

function extractWxmlText(node) {{
    var props = node.props || {{}};
    if (node.componentName === 'NutText' && props.text) return props.text;
    if (node.componentName === 'NutButton' && props.text) return props.text;
    if (node.componentName === 'NutEmpty' && props.description) return props.description;
    return null;
}}

main().catch(function(err) {{
    process.stderr.write(JSON.stringify({{ error: err.message, stack: err.stack }}));
    process.exit(1);
}});
"""


# ---------------------------------------------------------------------------
# CodegenService
# ---------------------------------------------------------------------------


class CodegenService:
    """低代码代码生成服务。

    通过 subprocess 调用 Node.js codegen 包完成实际的代码生成。
    """

    def __init__(self, db: Any):
        self.db = db

    async def generate_taro(
        self,
        page_id: str,
        tenant_id: str,
        output_format: str = "tsx",
    ) -> CodegenResult:
        """生成 Taro 小程序页面代码。

        Args:
            page_id: 低代码页面 ID
            tenant_id: 租户 ID
            output_format: 输出格式 (tsx)

        Returns:
            CodegenResult 包含生成的文件列表、警告、依赖等

        Raises:
            CodegenError: 生成失败时抛出
        """
        page = await self._load_page(page_id, tenant_id)
        schema = page.schema_data or {}
        data_sources = schema.get("dataSources", [])
        state = schema.get("state", {})

        return await self._run_codegen(
            schema=schema,
            data_sources=data_sources,
            state=state,
            target="taro",
            options={"outputFormat": output_format},
        )

    async def generate_native(
        self,
        page_id: str,
        tenant_id: str,
    ) -> CodegenResult:
        """生成原生微信小程序页面代码。

        Args:
            page_id: 低代码页面 ID
            tenant_id: 租户 ID

        Returns:
            CodegenResult 包含 .wxml / .wxss / .js / .json 文件

        Raises:
            CodegenError: 生成失败时抛出
        """
        page = await self._load_page(page_id, tenant_id)
        schema = page.schema_data or {}
        data_sources = schema.get("dataSources", [])
        state = schema.get("state", {})

        return await self._run_codegen(
            schema=schema,
            data_sources=data_sources,
            state=state,
            target="native",
            options={},
        )

    async def preview_codegen(
        self,
        schema: dict[str, Any],
        data_sources: list[dict[str, Any]],
        target: str = "taro",
    ) -> CodegenResult:
        """预览代码生成结果 (不持久化)。

        Args:
            schema: 页面 schema JSON
            data_sources: 数据源列表
            target: 目标平台 (taro / native)

        Returns:
            CodegenResult 预览结果

        Raises:
            CodegenError: 生成失败时抛出
        """
        state = schema.get("state", {})
        return await self._run_codegen(
            schema=schema,
            data_sources=data_sources,
            state=state,
            target=target,
            options={"preview": True},
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _load_page(self, page_id: str, tenant_id: str) -> Any:
        """从数据库加载低代码页面。"""
        from sqlalchemy import select

        from app.models.lowcode_page import LowCodePage

        query = select(LowCodePage).where(
            LowCodePage.id == page_id,
            LowCodePage.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        page = result.scalar_one_or_none()
        if not page:
            raise CodegenError(
                "页面不存在或无权访问",
                details={"page_id": page_id, "tenant_id": tenant_id},
            )
        return page

    async def _run_codegen(
        self,
        schema: dict[str, Any],
        data_sources: list[dict[str, Any]],
        state: dict[str, Any],
        target: str,
        options: dict[str, Any],
    ) -> CodegenResult:
        """执行 Node.js 代码生成 subprocess。"""
        codegen_bin = _get_codegen_bin()
        node_cmd = _get_node_cmd()
        timeout = _get_timeout()

        # 检查 codegen 入口是否存在
        if not Path(codegen_bin).exists():
            raise CodegenError(
                "代码生成器未构建。请先执行: cd packages/codegen && npm run build",
                details={"codegen_bin": codegen_bin},
            )

        # 查找独立的 cli-wrapper.js 文件
        wrapper_path = Path(__file__).parent.parent.parent.parent.parent / "packages" / "codegen" / "src" / "cli-wrapper.js"
        if not wrapper_path.exists():
            # 回退到内联 wrapper（兼容旧版）
            wrapper_path = None

        # 构造输入 JSON
        input_data = {
            "schema": schema,
            "dataSources": data_sources,
            "state": state,
            "target": target,
            "options": options,
        }
        input_json = json.dumps(input_data, ensure_ascii=False)

        if wrapper_path:
            # 使用独立的 cli-wrapper.js（无需生成临时脚本）
            script_path = str(wrapper_path)
            script_fd = None
        else:
            # 回退: 生成包装脚本 (使用真正的 codegen bin 路径)
            script_content = _NODEJS_WRAPPER.format(
                codegen_bin=codegen_bin.replace("\\", "/"),
            )
            script_fd, script_path = tempfile.mkstemp(suffix=".js", prefix="codegen_")
            os.write(script_fd, script_content.encode("utf-8"))
            os.close(script_fd)

        logger.info(
            "Running codegen: target=%s, schema_nodes=%d, ds_count=%d",
            target,
            _count_nodes(schema),
            len(data_sources),
        )

        # 执行 subprocess
        if script_fd is None:
            # 使用独立 cli-wrapper.js，传入 codegen 路径
            proc = await asyncio.create_subprocess_exec(
                node_cmd,
                script_path,
                codegen_bin.replace("\\", "/"),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            # 回退: 使用内联 wrapper（codegen 路径已嵌入脚本）
            proc = await asyncio.create_subprocess_exec(
                node_cmd,
                script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_json.encode("utf-8")),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise CodegenError(
                f"代码生成超时 ({timeout}秒)",
                details={"timeout": timeout, "target": target},
            )
        finally:
            # 清理临时文件（仅内联 wrapper 模式）
            if script_fd is not None:
                try:
                    os.unlink(script_path)
                except OSError:
                    pass

        # 处理 stderr (警告信息)
        stderr_text = stderr.decode("utf-8").strip() if stderr else ""
        if stderr_text:
            logger.warning("codegen stderr: %s", stderr_text)

        # 检查退出码
        if proc.returncode != 0:
            error_detail = {}
            if stderr_text:
                try:
                    error_detail = json.loads(stderr_text)
                except json.JSONDecodeError:
                    error_detail = {"raw": stderr_text}
            raise CodegenError(
                f"代码生成失败 (exit={proc.returncode}): {error_detail.get('error', stderr_text)}",
                details={"returncode": proc.returncode, **error_detail},
            )

        # 解析输出
        stdout_text = stdout.decode("utf-8").strip()
        if not stdout_text:
            raise CodegenError(
                "代码生成器无输出",
                details={"stderr": stderr_text},
            )

        try:
            output = json.loads(stdout_text)
        except json.JSONDecodeError as e:
            raise CodegenError(
                f"代码生成器输出非有效 JSON: {e}",
                details={"stdout_preview": stdout_text[:500]},
            )

        return self._parse_result(output)

    @staticmethod
    def _parse_result(output: dict[str, Any]) -> CodegenResult:
        """将 Node.js 输出解析为 CodegenResult。"""
        files = []
        for f in output.get("files", []):
            file_type_str = f.get("type", "tsx")
            try:
                file_type = GeneratedFileType(file_type_str)
            except ValueError:
                file_type = GeneratedFileType.TSX
            files.append(
                GeneratedFile(
                    path=f.get("path", "unknown"),
                    content=f.get("content", ""),
                    type=file_type,
                )
            )

        return CodegenResult(
            files=files,
            warnings=output.get("warnings", []),
            dependencies=output.get("dependencies", []),
            metadata=output.get("metadata", {}),
        )


def _count_nodes(schema: dict[str, Any]) -> int:
    """递归统计 schema 树中的节点数。"""
    count = 1
    for child in schema.get("children", []):
        if isinstance(child, dict):
            count += _count_nodes(child)
    return count
