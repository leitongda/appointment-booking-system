"""数据导入服务

提供数据导入的安全封装，确保：
1. 导入数据不能包含敏感字段（如 tenant_id）
2. 所有数据都使用调用方传入的租户锚点（R1-5：不回退请求上下文）
3. 行级别的租户隔离验证
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.excel.import_service import ExcelImportError, ExcelImportService
from app.middleware.exception import BusinessError

logger = logging.getLogger(__name__)

# 可能被恶意注入的敏感字段
SENSITIVE_FIELDS = {"tenant_id", "id", "created_at", "updated_at", "created_by", "updated_by"}


class ImportService:
    """数据导入基础服务

    提供数据导入的安全封装，确保：
    1. 导入数据不能包含敏感字段（如 tenant_id）
    2. 所有数据都使用调用方传入的租户锚点
    3. 行级别的租户隔离验证
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._tenant_id: str | None = None

    @staticmethod
    def _sanitize_row_data(row_data: dict[str, Any]) -> dict[str, Any]:
        """清理行数据，移除可能被恶意注入的敏感字段

        Args:
            row_data: 原始行数据

        Returns:
            清理后的行数据
        """
        return {
            k: v for k, v in row_data.items()
            if k not in SENSITIVE_FIELDS and not k.startswith("_")
        }

    def _infer_tenant_id(
        self,
        tenant_id: str | None = None,
        store_id: str | None = None
    ) -> str | None:
        """确定当前导入操作应使用的租户 ID

        R1-5：只接受显式锚点，不再回退请求上下文或按门店推断。
        调用方（router）负责从 `require_admin_tenant_anchor` 取得锚点。

        Args:
            tenant_id: 显式指定的租户ID（管理员账号锚点）
            store_id: 保留参数，当前不参与推断

        Returns:
            租户ID

        Raises:
            ValueError: 未显式提供租户 ID
        """
        # 使用缓存的租户 ID
        if self._tenant_id:
            return self._tenant_id

        if not tenant_id:
            raise ValueError("导入数据必须指定租户，请确保请求包含有效的租户锚点")

        # 缓存租户 ID
        self._tenant_id = tenant_id
        return tenant_id

    async def _validate_row_tenant(
        self,
        row_data: dict[str, Any],
        row_id: int,
        model_class: type | None = None,
        id_field: str | None = None
    ) -> str | None:
        """验证数据行是否属于当前租户

        对于包含关联 ID（如 patient_id, store_id）的导入数据，
        验证关联实体是否属于当前租户。

        Args:
            row_data: 行数据
            row_id: 行号（用于日志）
            model_class: 关联模型类（如 Patient, Store）
            id_field: 关联 ID 字段名（如 "patient_id", "store_id"）

        Returns:
            验证通过返回租户 ID，否则返回 None（跳过该行）

        Raises:
            ValueError: 关联数据不属于当前租户
        """
        current_tenant_id = self._tenant_id

        if not current_tenant_id:
            logger.warning(f"[导入] 行 {row_id}: 无法获取租户锚点，跳过验证")
            return None

        # 如果没有指定模型类，只验证租户上下文
        if not model_class or not id_field:
            return current_tenant_id

        # 获取关联 ID
        related_id = row_data.get(id_field)
        if not related_id:
            # 如果没有关联 ID，跳过验证
            return current_tenant_id

        # 查询关联实体
        try:
            result = await self.db.execute(
                select(model_class).where(model_class.id == related_id)
            )
            related_obj = result.scalar_one_or_none()

            if not related_obj:
                logger.warning(f"[导入] 行 {row_id}: 关联的 {id_field}={related_id} 不存在，跳过该行")
                return None

            # 验证租户一致性
            related_tenant_id = getattr(related_obj, 'tenant_id', None)
            if related_tenant_id and related_tenant_id != current_tenant_id:
                logger.warning(
                    f"[导入] 行 {row_id}: 数据与当前租户上下文不匹配，"
                    f"关联 {id_field}={related_id} 属于租户 {related_tenant_id}，"
                    f"当前租户为 {current_tenant_id}，跳过该行"
                )
                return None

            return current_tenant_id

        except Exception as e:
            logger.error(f"[导入] 行 {row_id}: 验证租户时发生错误: {e}")
            raise ValueError(f"验证数据租户时发生错误: {e}")

    async def validate_and_import(
        self,
        file_content: bytes,
        filename: str | None,
        expected_headers: list[str],
        required_fields: list[str],
        process_row_func,
        sanitize: bool = True,
        tenant_id: str | None = None,
        validate_tenant: bool = True,
    ) -> dict[str, Any]:
        """
        验证并导入数据

        Args:
            file_content: Excel 文件内容
            filename: 文件名
            expected_headers: 期望的表头
            required_fields: 必填字段
            process_row_func: 处理单行数据的异步函数
            sanitize: 是否清理敏感字段（默认True）
            tenant_id: 显式指定的租户ID（可选）
            validate_tenant: 是否验证租户上下文（默认True）

        Returns:
            导入结果统计

        Raises:
            BusinessError: 导入文件包含敏感字段或租户验证失败时抛出异常
        """
        # 验证租户上下文
        if validate_tenant:
            try:
                effective_tenant_id = self._infer_tenant_id(tenant_id=tenant_id)
                logger.info(f"[导入] 开始导入数据，租户 ID: {effective_tenant_id}")
            except ValueError as e:
                raise BusinessError(str(e), code=400) from e
        else:
            effective_tenant_id = None

        # 解析 Excel
        try:
            valid_rows, error_rows = ExcelImportService.parse_excel(
                file_content,
                expected_headers,
                required_fields,
                filename=filename,
            )
        except ExcelImportError as exc:
            raise BusinessError(str(exc), code=400) from exc

        # 安全检查：确保导入数据不包含敏感字段
        if sanitize and valid_rows:
            for row_data in valid_rows:
                # 检查是否包含敏感字段（而不是通过长度比较，因为 _sanitize_row_data 还会移除 _row 等内部字段）
                detected_fields = set(row_data.keys()) & SENSITIVE_FIELDS
                if detected_fields:
                    raise BusinessError(
                        f"导入数据包含不允许的字段: {', '.join(detected_fields)}。"
                        f"敏感字段（tenant_id, id等）由系统自动设置，请勿在导入文件中填写。",
                        code=400
                    )
                cleaned_data = self._sanitize_row_data(row_data)
                # 更新为清理后的数据
                row_data.clear()
                row_data.update(cleaned_data)

        success_count = 0
        fail_count = len(error_rows)
        skipped_count = 0

        # 处理有效数据
        for row_data in valid_rows:
            row_id = row_data.get("_row", 0)
            try:
                # 将租户 ID 传递给处理函数（通过闭包变量）
                # 处理函数可以使用 self._tenant_id 获取租户 ID
                await process_row_func(row_data)
                success_count += 1
            except ValueError as e:
                # 租户验证失败，跳过该行（不作为错误）
                if "租户" in str(e) or "不存在" in str(e):
                    logger.warning(f"[导入] 行 {row_id}: {e}，跳过该行")
                    skipped_count += 1
                else:
                    fail_count += 1
                    error_rows.append({
                        "row": row_id,
                        "data": {k: v for k, v in row_data.items() if not k.startswith("_")},
                        "errors": [str(e)]
                    })
            except Exception as e:
                fail_count += 1
                error_rows.append({
                    "row": row_id,
                    "data": {k: v for k, v in row_data.items() if not k.startswith("_")},
                    "errors": [str(e)]
                })

        await self.db.commit()

        # 记录导入日志
        if effective_tenant_id:
            logger.info(
                f"[导入] 导入完成 - 租户: {effective_tenant_id}, "
                f"成功: {success_count}, 失败: {fail_count}, 跳过: {skipped_count}"
            )

        return {
            "success_count": success_count,
            "fail_count": fail_count,
            "skipped_count": skipped_count,
            "total": success_count + fail_count + skipped_count,
            "errors": error_rows[:50]  # 最多返回50条错误
        }

    @property
    def tenant_id(self) -> str | None:
        """获取当前导入操作的租户 ID"""
        return self._tenant_id
