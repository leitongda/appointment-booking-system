#!/usr/bin/env python3
"""生成 docs/modules/permission-codes.md（openspec refactor-admin-permission-classification 0.1）

权限码 ↔ 后端守卫端点 ↔ 前端引用 的使用关系清单，供权限分配页与代码评审对照。

数据来源（全部静态解析，不连库）：
1. 权限目录：scripts/init_permissions.py 的 PERMISSIONS（种子，source of truth）；
2. 后端守卫：app/modules/**/*.py 中 require_permission / require_all_permissions /
   require_account_permission / require_account_all_permissions 的实参权限码；
3. 前端引用：apps/admin/src/**/*.{ts,tsx} 中出现的权限码字符串。

同时输出两类漂移信号：
- 后端守卫使用了目录中不存在的码（拼写错误会直接 403 且无法授权）；
- 目录中从未被前后端引用的「展示型」码。

使用方法:
    python scripts/gen_permission_matrix.py            # 写入 docs/modules/permission-codes.md
    python scripts/gen_permission_matrix.py --check     # 只做漂移检查，退出码 1 表示有漂移（可挂 CI）
"""
import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent          # apps/server
REPO_ROOT = SERVER_ROOT.parent.parent
SEED = SERVER_ROOT / "scripts" / "init_permissions.py"
OUT = REPO_ROOT / "docs" / "modules" / "permission-codes.md"

GUARD_FACTORIES = {
    "require_permission",
    "require_all_permissions",
    "require_account_permission",
    "require_account_all_permissions",
}
GUARD_CALL = re.compile(
    r"(require_permission|require_all_permissions|require_account_permission|require_account_all_permissions)\(([^)]*)\)"
)


def load_catalog() -> list[dict]:
    tree = ast.parse(SEED.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PERMISSIONS":
            return [dict(elt) if not isinstance(elt, ast.Dict) else {
                k.value if isinstance(k, ast.Constant) else "?": (
                    v.value if isinstance(v, ast.Constant) else None
                )
                for k, v in zip(elt.keys, elt.values)
            } for elt in node.value.elts]
    raise RuntimeError("PERMISSIONS 未在 init_permissions.py 中找到")


def scan_backend() -> dict[str, set[str]]:
    """权限码 -> {module_path:line, ...}（app/modules 下守卫调用处）"""
    usage: dict[str, set[str]] = defaultdict(set)
    for path in (SERVER_ROOT / "app" / "modules").rglob("*.py"):
        rel = path.relative_to(SERVER_ROOT)
        text = path.read_text(encoding="utf-8")
        for match in GUARD_CALL.finditer(text):
            factory, args = match.group(1), match.group(2)
            if factory not in GUARD_FACTORIES:
                continue  # 注释或同名局部变量
            for code in re.findall(r"'([^']+)'|\"([^\"]+)\"", args):
                code_value = code[0] or code[1]
                line = text[: match.start()].count("\n") + 1
                usage[code_value].add(f"{rel}:{line}")
    return usage


def scan_frontend(codes: list[str]) -> dict[str, set[str]]:
    """权限码 -> {admin_src 相对路径, ...}"""
    usage: dict[str, set[str]] = defaultdict(set)
    admin_src = REPO_ROOT / "apps" / "admin" / "src"
    files = list(admin_src.rglob("*.ts")) + list(admin_src.rglob("*.tsx"))
    code_set = set(codes)
    for path in files:
        rel = str(path.relative_to(admin_src))
        text = path.read_text(encoding="utf-8")
        for code in code_set:
            if f"'{code}'" in text or f'"{code}"' in text:
                usage[code].add(rel)
    return usage


def main(check_only: bool = False) -> int:
    catalog = load_catalog()
    catalog_codes = [entry["code"] for entry in catalog]
    backend = scan_backend()
    frontend = scan_frontend(catalog_codes)

    # 漂移：守卫用了目录外的码
    drift = sorted(set(backend) - set(catalog_codes))
    # 展示型：目录内但前后端零引用
    display_only = sorted(
        code for code in catalog_codes if code not in backend and code not in frontend
    )

    if check_only:
        for code in drift:
            print(f"DRIFT: 后端守卫使用目录外权限码 {code} @ {sorted(backend[code])}")
        print(f"check 完成：漂移 {len(drift)} 个，展示型 {len(display_only)} 个")
        return 1 if drift else 0

    children: dict[str | None, list[dict]] = defaultdict(list)
    for entry in catalog:
        children[entry.get("parent_code")].append(entry)
    for group in children.values():
        group.sort(key=lambda e: (e.get("sort") or 0, e["code"]))

    lines = [
        "# 权限码使用关系清单",
        "",
        "> 由 `apps/server/scripts/gen_permission_matrix.py` 生成，请勿手改；",
        "> 权限目录的 source of truth 是 `apps/server/scripts/init_permissions.py`。",
        "",
        f"- 目录权限码：{len(catalog)} 个",
        f"- 后端守卫引用：{len(backend)} 个码",
        f"- 前端（admin）引用：{len(frontend)} 个码",
        f"- 后端守卫使用但目录缺失（漂移，需修）：{len(drift)} 个",
        f"- 目录内但前后端零引用（展示型）：{len(display_only)} 个",
        "",
        "后端列格式为 `模块路径:行号`（`require_permission` 族调用处）；前端列为 admin 源码引用文件数。",
        "",
    ]

    if drift:
        lines += ["## ⚠️ 目录外权限码（守卫在用、无法授权）", ""]
        lines += ["| 权限码 | 后端调用处 |", "|---|---|"]
        for code in drift:
            lines.append(f"| `{code}` | {'; '.join(sorted(backend[code]))} |")
        lines.append("")

    for top in children.get(None, []):
        module_name = top["name"]
        lines += [f"## {module_name}（`{top['code']}`）", ""]
        lines += ["| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |", "|---|---|---|---|---|"]

        def render(entry: dict) -> None:
            code = entry["code"]
            backend_refs = sorted(backend.get(code, []))
            frontend_count = len(frontend.get(code, []))
            indent = "&nbsp;&nbsp;" * (
                0 if entry.get("parent_code") is None else 1
            )
            lines.append(
                f"| {indent}`{code}` | {entry['name']} | {entry['type']} | "
                f"{'; '.join(backend_refs) or '—'} | {frontend_count or '—'} |"
            )
            for child in children.get(code, []):
                render(child)

        render(top)
        lines.append("")

    if display_only:
        lines += ["## 展示型权限码（前后端零引用，可评估下线或接线）", "", "```"]
        lines += ["; ".join(display_only[i : i + 6]) for i in range(0, len(display_only), 6)]
        lines += ["```", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {OUT.relative_to(REPO_ROOT)}: {len(catalog)} codes, drift={len(drift)}, display_only={len(display_only)}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只做漂移检查（退出码 1=有漂移，可挂 CI）")
    args = parser.parse_args()
    sys.exit(main(check_only=args.check))
