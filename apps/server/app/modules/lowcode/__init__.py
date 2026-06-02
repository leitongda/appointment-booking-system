"""低代码搭建模块。"""

from app.modules.lowcode.router import router as lowcode_router
from app.modules.lowcode.router_template import router as template_router

__all__ = ["lowcode_router", "template_router"]
