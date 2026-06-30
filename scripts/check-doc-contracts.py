#!/usr/bin/env python3
"""文档契约校验脚本。

防止 README.md / CLAUDE.md 中的关键工程数字与代码实际值脱节。
权威源：代码本身（路由注册表、模型类）。文档声明若与代码不符则非零退出。

用法:
    python scripts/check-doc-contracts.py          # 校验，不一致则 exit 1
    python scripts/check-doc-contracts.py --report  # 仅打印报告，不退出

背景：历史曾出现 CLAUDE.md 同文件内 L118 写 "82 个模块"、L307 写 "81 个模块"
自相矛盾，且都与实际值（84）不符。此脚本在 CI 中作为文档契约门禁运行。

运行前提：需能 import apps/server 的 app 包（设置 PYTHONPATH 或在 apps/server 下运行）。
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 项目根目录（scripts/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVER_ROOT = PROJECT_ROOT / "apps" / "server"

# 待校验文档（相对项目根）
DOC_FILES = ["README.md", "CLAUDE.md"]


@dataclass
class Metric:
    """一个可校验的工程指标。"""

    name: str
    actual: int
    patterns: list[re.Pattern[str]]
    # 允许的容差：文档里写 "40+" 这类约数时，只要 actual >= 阈值即视为通过
    min_acceptable: int

    def check(self, doc_text: str, doc_name: str) -> list[str]:
        """检查文档中与该指标相关的所有数字声明。返回错误信息列表。"""
        errors: list[str] = []
        for pat in self.patterns:
            for m in pat.finditer(doc_text):
                declared = int(m.group("n"))
                # 约数声明（如 "40+"）允许 actual 更大；精确数字必须完全匹配
                if m.group().rstrip().endswith("+"):
                    if self.actual < self.min_acceptable:
                        errors.append(
                            f"{doc_name}: 声明 '{m.group().strip()}'，"
                            f"但实际值 {self.actual} 低于该下限声明"
                        )
                elif declared != self.actual:
                    errors.append(
                        f"{doc_name} 第 {doc_text[: m.start()].count(chr(10)) + 1} 行: "
                        f"声明 {self.name}={declared}，实际为 {self.actual}"
                    )
        return errors


def collect_actual_metrics() -> dict[str, Metric]:
    """从代码权威源采集实际值。需要能 import app 包。"""
    sys.path.insert(0, str(SERVER_ROOT))

    # 1. 路由注册数（权威：ROUTER_REGISTRATIONS）
    from app.api.v1 import ROUTER_REGISTRATIONS  # type: ignore[import-not-found]

    router_count = len(ROUTER_REGISTRATIONS)

    # 2. 模型类数（权威：app/models 下所有 Base 子类，含多继承如 Base, AuditMixin）
    import re as _re

    # 匹配 class X(Base) 和 class X(Base, OtherMixin) 两种形式
    model_pattern = _re.compile(r"^class [A-Z][A-Za-z0-9_]*\(Base[,:]?\)?")
    models_dir = SERVER_ROOT / "app" / "models"
    model_count = 0
    for py_file in models_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        for line in py_file.read_text(encoding="utf-8").splitlines():
            if model_pattern.match(line):
                model_count += 1

    # 路由数：文档中可能写成 "84 个模块" 或 "84 条路由" 或 "60+ 模块"
    router_patterns = [
        re.compile(r"(?<![\d.])(?P<n>\d{2,3})\s*(?:个模块|条路由注册|个模块动态)", re.MULTILINE),
    ]
    model_patterns = [
        re.compile(r"(?P<n>\d{2,3})\s*个模型类"),
        re.compile(r"(?P<n>\d{2,3})\+?\s*表"),
    ]

    return {
        "router": Metric(
            name="路由模块数",
            actual=router_count,
            patterns=router_patterns,
            # 约数声明容差：文档写 "80+" 时实际不得低于 80
            min_acceptable=router_count,
        ),
        "model": Metric(
            name="模型类数",
            actual=model_count,
            patterns=model_patterns,
            min_acceptable=model_count,
        ),
    }


def main() -> int:
    report_only = "--report" in sys.argv

    try:
        metrics = collect_actual_metrics()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 无法从代码采集权威值（是否在项目根目录运行？）: {exc}", file=sys.stderr)
        print(
            f"   提示：在 apps/server 下运行，或设置 PYTHONPATH={SERVER_ROOT}",
            file=sys.stderr,
        )
        return 2

    print("=" * 60)
    print("文档契约校验报告")
    print("=" * 60)
    print(f"代码权威值：路由模块数={metrics['router'].actual}, "
          f"模型类数={metrics['model'].actual}")
    print("-" * 60)

    all_errors: list[str] = []
    for doc_name in DOC_FILES:
        doc_path = PROJECT_ROOT / doc_name
        if not doc_path.exists():
            print(f"⚠️  跳过不存在的文档: {doc_name}")
            continue
        doc_text = doc_path.read_text(encoding="utf-8")
        doc_errors: list[str] = []
        for metric in metrics.values():
            doc_errors.extend(metric.check(doc_text, doc_name))
        if doc_errors:
            for e in doc_errors:
                print(f"  ❌ {e}")
            all_errors.extend(doc_errors)
        else:
            print(f"  ✅ {doc_name}: 所有数字声明与代码一致")

    print("-" * 60)
    if all_errors:
        print(f"❌ 发现 {len(all_errors)} 处文档与代码不一致")
        if not report_only:
            print("   请更新文档使其与代码实际值匹配，或运行本脚本确认。")
            return 1
        print("   (--report 模式，不阻断)")
        return 0
    print("✅ 文档契约校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
