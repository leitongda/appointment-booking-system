# 架构 Fitness Functions — 审计报告与实施方案

**日期**: 2026-06-04
**参考**: 《Building Evolutionary Architectures》(Ford, Parsons, Kua, O'Reilly 2017)

---

## 理论基础

### 什么是 Fitness Function

《Building Evolutionary Architectures》定义：**Fitness Function 是对架构特征进行客观、自动化、持续性完整性评估的机制**，源自进化计算中的适应度概念。

核心属性：
1. **客观性** — 基于可量化指标，非主观判断
2. **自动化** — 嵌入 CI/CD，无需人工触发
3. **持续性** — 每次代码变更自动验证
4. **针对架构特征** — 依赖方向、耦合度、模块边界等

### 架构度量指标体系

| 指标 | 公式 | 用途 |
|------|------|------|
| **Fan-in (Ca)** | 调用该模块的其他模块数 | 稳定性指标，高 fan-in = 核心模块 |
| **Fan-out (Ce)** | 该模块调用的其他模块数 | 依赖复杂度 |
| **Instability (I)** | Ce / (Ca + Ce) | 0=稳定(被依赖多)，1=不稳定(依赖多) |
| **Distance (D)** | \|A + I - 1\| | 偏离主序列距离，< 0.3 为健康 |

### Python 生态工具

| 工具 | 能力 | 适用场景 |
|------|------|---------|
| **import-linter** | import 依赖合约检查（Layers/Forbidden/Independence 等 6 种） | 架构分层约束 |
| **pydeps** | 依赖图可视化 | 依赖分析 |
| **vulture** | 死代码检测 | 代码卫生 |
| **ruff** | 代码风格 + 常见错误 | 已集成 |

---

## 项目现状审计

### 已有的 Fitness Functions（CI 管道）

| 检查 | 工具 | 覆盖维度 |
|------|------|---------|
| 单元测试 | pytest | 功能正确性 |
| 集成测试 | pytest + PostgreSQL | 数据库交互 |
| 代码风格 | ruff check/format | 代码质量 |
| 依赖漏洞 | pip-audit | 安全 |
| 镜像扫描 | Trivy | 安全 |

### 缺失的架构级 Fitness Functions

| 缺失检查 | 风险 | 当前状态 |
|----------|------|---------|
| 模块间依赖方向 | 分层被破坏 | 无自动化检查 |
| 循环依赖 | 启动失败风险 | 仅靠 lazy import 缓解 |
| 模块大小阈值 | God File | 无自动化检查 |
| 新模块必须有测试 | 覆盖率下降 | 无自动化检查 |
| API 路由必须有认证 | 安全漏洞 | 无自动化检查 |
| 枚举一致性 | 硬编码字符串 | 无自动化检查 |

---

## 实施方案

### Fitness Function #1: 分层依赖合约

**规则**: `api -> modules -> common -> infrastructure -> core`

```
# import-linter 合约配置
[layers]
name = 分层架构
type = layers
layers =
    app.api
    app.modules
    app.common
    app.infrastructure
    app.core
    app.db
    app.middleware
```

### Fitness Function #2: 模块独立性

**规则**: 62 个 modules/ 下的业务模块不应互相导入（共享常量除外）

```
[independence]
name = 业务模块独立性
type = independence
modules =
    app.modules.appointments
    app.modules.doctors
    app.modules.schedules
    app.modules.patients
    app.modules.payments
    app.modules.refunds
    ...
```

### Fitness Function #3: 禁止危险依赖

**规则**: infrastructure 不应直接导入 modules

```
[forbid-infrastructure-to-modules]
name = 基础设施禁止依赖业务模块
type = forbidden
source_modules = app.infrastructure
forbidden_modules = app.modules
```

### Fitness Function #4: 模块大小阈值

**规则**: 单文件不超过阈值

```python
# 自定义 fitness function 脚本
def check_file_sizes():
    THRESHOLDS = {
        'router.py': 300,
        'service.py': 500,
        'schemas.py': 200,
    }
    violations = []
    for path in Path('app/modules').rglob('*.py'):
        lines = len(path.read_text().splitlines())
        for pattern, limit in THRESHOLDS.items():
            if path.name == pattern and lines > limit:
                violations.append(f'{path}: {lines} lines > {limit}')
    return violations
```

### Fitness Function #5: 新模块必须有测试

**规则**: modules/ 下有 service.py 的模块，tests/ 中必须有对应测试

```python
def check_test_coverage():
    modules = [d.name for d in Path('app/modules').iterdir() 
               if d.is_dir() and (d / 'service.py').exists()]
    tests = [f.stem.replace('test_', '') for f in Path('tests/unit').glob('test_*.py')]
    missing = [m for m in modules if m not in tests]
    return missing
```

### Fitness Function #6: API 路由认证

**规则**: 除 /public/* 和 /auth/* 外，所有路由需 get_current_account

```python
def check_auth_coverage():
    # 解析 router.py 中的路由定义，检查 Depends(get_current_account)
    ...
```

---

## 集成方式

### 方案 A: import-linter（推荐）

```bash
pip install import-linter
```

创建 `setup.cfg` 或 `importlinter.ini`:

```ini
[importlinter]
root_package = app

[layers]
name = 分层架构
type = layers
layers =
    app.api
    app.modules
    app.common
    app.infrastructure
    app.core

[forbid-infra-to-modules]
name = 基础设施禁止依赖业务模块
type = forbidden
source_modules = app.infrastructure
forbidden_modules = app.modules
```

CI 集成: 在 `.github/workflows/test.yml` 中添加 `lint-imports` 步骤。

### 方案 B: 自定义 pytest 插件

```python
# tests/architecture/test_fitness_functions.py
import pytest
from pathlib import Path

class TestArchitectureFitness:
    def test_no_circular_imports(self):
        """模块间不应有循环依赖"""
        ...

    def test_file_size_limits(self):
        """单文件不超过阈值"""
        ...

    def test_all_modules_have_tests(self):
        """每个业务模块必须有测试"""
        ...

    def test_auth_coverage(self):
        """API 路由必须有认证"""
        ...
```

---

## 推荐实施路径

1. **第一步**: 安装 import-linter，配置 Layers 合约（分层依赖）
2. **第二步**: 配置 Independence 合约（模块独立性）
3. **第三步**: 编写自定义 pytest fitness functions（文件大小、测试覆盖、认证覆盖）
4. **第四步**: 集成到 CI 管道（test.yml 添加 lint-imports + pytest -m architecture）
5. **第五步**: 设置 pre-commit hook，本地提交前验证

---

## 参考来源

- Ford, Parsons, Kua. *Building Evolutionary Architectures*. O'Reilly, 2017.
- ThoughtWorks Technology Radar: Architectural Fitness Function
- ArchUnit: https://www.archunit.org/
- import-linter: https://import-linter.readthedocs.io/
- Robert C. Martin. *Clean Architecture*. Prentice Hall, 2017.
- John Lakos. *Large-Scale C++ Software Design*. Addison-Wesley, 1996.
