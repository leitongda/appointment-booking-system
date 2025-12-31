"""为已有的就诊卡补充卡号"""
import asyncio
import sys
import os
import random
import string
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, or_
from app.db.session import AsyncSessionLocal
from app.models.user import Patient


def generate_card_no() -> str:
    """生成就诊卡编号"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=4))
    return f"JZK{timestamp}{random_str}"


async def fix_patient_card_no():
    """为没有卡号的就诊卡补充卡号"""
    async with AsyncSessionLocal() as db:
        print("=" * 50)
        print("为就诊卡补充卡号")
        print("=" * 50)
        
        # 1. 查找所有没有卡号的就诊卡
        result = await db.execute(
            select(Patient).where(
                or_(
                    Patient.card_no.is_(None),
                    Patient.card_no == ""
                )
            )
        )
        patients = result.scalars().all()
        
        if not patients:
            print("✓ 所有就诊卡都已有卡号，无需修复")
            return
        
        print(f"找到 {len(patients)} 张没有卡号的就诊卡")
        print()
        
        # 2. 为每张就诊卡生成卡号
        updated_count = 0
        for patient in patients:
            card_no = generate_card_no()
            patient.card_no = card_no
            updated_count += 1
            print(f"  [{updated_count}] {patient.name} -> {card_no}")
            # 添加微小延迟确保时间戳不重复
            await asyncio.sleep(0.01)
        
        # 3. 提交更改
        await db.commit()
        
        print()
        print("=" * 50)
        print(f"✅ 已为 {updated_count} 张就诊卡补充卡号")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(fix_patient_card_no())

