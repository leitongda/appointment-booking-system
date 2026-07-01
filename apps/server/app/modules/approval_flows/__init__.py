"""通用审批流引擎模块。

引擎包零业务依赖（开闭原则）：业务模块自行实现回调并在各自 ``__init__.py``
通过 ``callback_registry.register(...)`` 注册，本包不再 import 任何业务 service，
从而避免循环依赖。
"""
