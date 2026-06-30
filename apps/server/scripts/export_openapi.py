#!/usr/bin/env python3
"""导出后端 OpenAPI schema 到前端仓库，供 openapi-typescript 生成类型。

用途：
    python apps/server/scripts/export_openapi.py

将后端 FastAPI 应用的完整 OpenAPI schema 导出为 JSON，
写入 packages/shared/src/types/api-generated/openapi.json，
作为前端类型自动生成（pnpm gen:api-types）的输入。

这是「前后端类型契约自动对齐」流水线的第一步——后端是类型的唯一真相源。
手动触发：后端 schema 变更后运行此脚本 + 前端 gen:api-types，即可同步类型。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 脚本位于 apps/server/scripts/export_openapi.py
# parent=scripts, parent.parent=server, parent.parent.parent.parent=项目根
SCRIPT_DIR = Path(__file__).resolve().parent
SERVER_ROOT = SCRIPT_DIR.parent  # apps/server
PROJECT_ROOT = SERVER_ROOT.parent.parent  # 项目根

# 输出位置：前端 shared 包的 api-generated 目录
OUTPUT_DIR = PROJECT_ROOT / "packages" / "shared" / "src" / "types" / "api-generated"
OUTPUT_FILE = OUTPUT_DIR / "openapi.json"


def main() -> int:
    print("导出后端 OpenAPI schema...")

    # app.main 依赖 apps/server 作为工作目录（加载 .env、日志路径等），
    # 切换到该目录后再加入 sys.path
    import os

    os.chdir(SERVER_ROOT)
    sys.path.insert(0, str(SERVER_ROOT))

    # 导入后端 app（触发 FastAPI 应用装配，所有路由/schema 注册）
    from app.main import app  # type: ignore[import-not-found]

    schema = app.openapi()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

    path_count = len(schema.get("paths", {}))
    schema_count = len(schema.get("components", {}).get("schemas", {}))
    size_kb = OUTPUT_FILE.stat().st_size / 1024

    print(f"✓ OpenAPI schema 已导出")
    print(f"  路径数: {path_count}")
    print(f"  Schema 数: {schema_count}")
    print(f"  文件大小: {size_kb:.1f} KB")
    print(f"  输出位置: {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")
    print()
    print("下一步：在项目根运行 `pnpm gen:api-types` 生成 TypeScript 类型")
    return 0


if __name__ == "__main__":
    sys.exit(main())
