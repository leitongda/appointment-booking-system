"""数据导入服务"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date

from app.services.excel_service import ExcelImportService


class ImportService:
    """数据导入基础服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_and_import(
        self,
        file_content: bytes,
        expected_headers: List[str],
        required_fields: List[str],
        process_row_func,
    ) -> Dict[str, Any]:
        """
        验证并导入数据

        Args:
            file_content: Excel 文件内容
            expected_headers: 期望的表头
            required_fields: 必填字段
            process_row_func: 处理单行数据的异步函数

        Returns:
            导入结果统计
        """
        # 解析 Excel
        valid_rows, error_rows = ExcelImportService.parse_excel(
            file_content,
            expected_headers,
            required_fields
        )

        success_count = 0
        fail_count = len(error_rows)

        # 处理有效数据
        for row_data in valid_rows:
            try:
                await process_row_func(row_data)
                success_count += 1
            except Exception as e:
                fail_count += 1
                error_rows.append({
                    "row": row_data.get("_row", 0),
                    "data": row_data,
                    "errors": [str(e)]
                })

        await self.db.commit()

        return {
            "success_count": success_count,
            "fail_count": fail_count,
            "total": success_count + fail_count,
            "errors": error_rows[:50]  # 最多返回50条错误
        }
