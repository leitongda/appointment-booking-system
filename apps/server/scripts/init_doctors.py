"""初始化测试医生数据"""
import asyncio
import sys
import os
import uuid

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import bcrypt

from app.core.config import settings as app_settings
from app.models.doctor import Doctor
from app.models.department import Department


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def init_doctors():
    """初始化测试医生"""
    engine = create_async_engine(app_settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 获取所有科室
        dept_names = ["内科", "外科", "儿科", "妇产科", "眼科", "口腔科", "皮肤科", "中医科"]
        departments = {}
        
        for name in dept_names:
            result = await session.execute(select(Department).where(Department.name == name))
            dept = result.scalar_one_or_none()
            if dept:
                departments[name] = dept
        
        if not departments:
            print("请先初始化科室数据")
            return
        
        print(f"已找到 {len(departments)} 个科室: {', '.join(departments.keys())}")
        
        doctors_data = [
            # ========== 内科医生 ==========
            {
                "name": "张明华",
                "phone": "13900000001",
                "password": "doctor123",
                "department": "内科",
                "title": "主任医师",
                "specialty": "心血管疾病、高血压、冠心病",
                "introduction": "从医30年，擅长心血管疾病诊治，曾在北京协和医院进修学习。",
                "is_recommended": 1,
            },
            {
                "name": "李秀芳",
                "phone": "13900000002",
                "password": "doctor123",
                "department": "内科",
                "title": "副主任医师",
                "specialty": "呼吸系统疾病、肺炎、哮喘",
                "introduction": "呼吸内科专家，擅长各类呼吸系统疾病的诊断与治疗。",
                "is_recommended": 1,
            },
            {
                "name": "陈建国",
                "phone": "13900000003",
                "password": "doctor123",
                "department": "内科",
                "title": "主治医师",
                "specialty": "消化系统疾病、胃肠病",
                "introduction": "消化内科医师，专注于胃肠道疾病的诊治。",
                "is_recommended": 0,
            },
            {
                "name": "刘志强",
                "phone": "13900000004",
                "password": "doctor123",
                "department": "内科",
                "title": "副主任医师",
                "specialty": "糖尿病、内分泌疾病",
                "introduction": "内分泌专家，在糖尿病及甲状腺疾病治疗方面有丰富经验。",
                "is_recommended": 1,
            },
            
            # ========== 外科医生 ==========
            {
                "name": "王伟民",
                "phone": "13900000011",
                "password": "doctor123",
                "department": "外科",
                "title": "主任医师",
                "specialty": "普外科手术、腹腔镜微创手术",
                "introduction": "外科专家，擅长微创手术，主刀手术超过5000台。",
                "is_recommended": 1,
            },
            {
                "name": "赵海龙",
                "phone": "13900000012",
                "password": "doctor123",
                "department": "外科",
                "title": "副主任医师",
                "specialty": "骨科手术、关节置换",
                "introduction": "骨科专家，擅长关节置换及骨折复位手术。",
                "is_recommended": 1,
            },
            {
                "name": "孙国庆",
                "phone": "13900000013",
                "password": "doctor123",
                "department": "外科",
                "title": "主治医师",
                "specialty": "甲状腺、乳腺外科",
                "introduction": "专注于甲状腺和乳腺疾病的外科治疗。",
                "is_recommended": 0,
            },
            
            # ========== 儿科医生 ==========
            {
                "name": "林小燕",
                "phone": "13900000021",
                "password": "doctor123",
                "department": "儿科",
                "title": "主任医师",
                "specialty": "小儿呼吸系统疾病、新生儿疾病",
                "introduction": "儿科专家，从医25年，对儿童常见病、多发病有丰富经验。",
                "is_recommended": 1,
            },
            {
                "name": "黄晓玲",
                "phone": "13900000022",
                "password": "doctor123",
                "department": "儿科",
                "title": "副主任医师",
                "specialty": "小儿消化系统疾病、营养不良",
                "introduction": "擅长小儿消化系统疾病诊治，在儿童营养指导方面有专长。",
                "is_recommended": 1,
            },
            {
                "name": "周婷婷",
                "phone": "13900000023",
                "password": "doctor123",
                "department": "儿科",
                "title": "主治医师",
                "specialty": "儿童保健、预防接种",
                "introduction": "专注于儿童保健和预防医学，致力于儿童健康成长。",
                "is_recommended": 0,
            },
            
            # ========== 妇产科医生 ==========
            {
                "name": "吴美玲",
                "phone": "13900000031",
                "password": "doctor123",
                "department": "妇产科",
                "title": "主任医师",
                "specialty": "高危妊娠、产前诊断",
                "introduction": "产科专家，擅长高危妊娠管理和产前诊断。",
                "is_recommended": 1,
            },
            {
                "name": "郑丽华",
                "phone": "13900000032",
                "password": "doctor123",
                "department": "妇产科",
                "title": "副主任医师",
                "specialty": "妇科肿瘤、宫腔镜手术",
                "introduction": "妇科专家，擅长妇科肿瘤诊治和微创手术。",
                "is_recommended": 1,
            },
            {
                "name": "何雪梅",
                "phone": "13900000033",
                "password": "doctor123",
                "department": "妇产科",
                "title": "主治医师",
                "specialty": "妇科炎症、月经不调",
                "introduction": "专注于妇科常见病的诊治，擅长中西医结合治疗。",
                "is_recommended": 0,
            },
            
            # ========== 眼科医生 ==========
            {
                "name": "杨光明",
                "phone": "13900000041",
                "password": "doctor123",
                "department": "眼科",
                "title": "主任医师",
                "specialty": "白内障、青光眼手术",
                "introduction": "眼科专家，擅长白内障超声乳化手术和青光眼治疗。",
                "is_recommended": 1,
            },
            {
                "name": "徐明亮",
                "phone": "13900000042",
                "password": "doctor123",
                "department": "眼科",
                "title": "副主任医师",
                "specialty": "近视矫正、角膜病",
                "introduction": "擅长激光近视矫正手术和角膜疾病治疗。",
                "is_recommended": 1,
            },
            {
                "name": "马晓东",
                "phone": "13900000043",
                "password": "doctor123",
                "department": "眼科",
                "title": "主治医师",
                "specialty": "眼底病、视网膜疾病",
                "introduction": "专注于眼底疾病诊治，擅长眼底激光治疗。",
                "is_recommended": 0,
            },
            
            # ========== 口腔科医生 ==========
            {
                "name": "胡德贵",
                "phone": "13900000051",
                "password": "doctor123",
                "department": "口腔科",
                "title": "主任医师",
                "specialty": "口腔种植、颌面外科",
                "introduction": "口腔种植专家，完成种植手术超过3000例。",
                "is_recommended": 1,
            },
            {
                "name": "钱佳琪",
                "phone": "13900000052",
                "password": "doctor123",
                "department": "口腔科",
                "title": "副主任医师",
                "specialty": "牙齿正畸、美容修复",
                "introduction": "正畸专家，擅长各类牙齿矫正和美学修复。",
                "is_recommended": 1,
            },
            {
                "name": "高建峰",
                "phone": "13900000053",
                "password": "doctor123",
                "department": "口腔科",
                "title": "主治医师",
                "specialty": "牙体牙髓、根管治疗",
                "introduction": "专注于牙体牙髓病治疗，擅长复杂根管治疗。",
                "is_recommended": 0,
            },
            
            # ========== 皮肤科医生 ==========
            {
                "name": "冯雅琴",
                "phone": "13900000061",
                "password": "doctor123",
                "department": "皮肤科",
                "title": "主任医师",
                "specialty": "皮肤病、性病诊治",
                "introduction": "皮肤科专家，从医28年，对各类皮肤病有丰富诊疗经验。",
                "is_recommended": 1,
            },
            {
                "name": "曹静怡",
                "phone": "13900000062",
                "password": "doctor123",
                "department": "皮肤科",
                "title": "副主任医师",
                "specialty": "皮肤美容、激光治疗",
                "introduction": "擅长皮肤美容和激光治疗，在祛斑、祛痘方面有专长。",
                "is_recommended": 1,
            },
            {
                "name": "蒋文博",
                "phone": "13900000063",
                "password": "doctor123",
                "department": "皮肤科",
                "title": "主治医师",
                "specialty": "过敏性皮肤病、湿疹",
                "introduction": "专注于过敏性皮肤病诊治，擅长中西医结合治疗湿疹、荨麻疹。",
                "is_recommended": 0,
            },
            
            # ========== 中医科医生 ==========
            {
                "name": "沈德仁",
                "phone": "13900000071",
                "password": "doctor123",
                "department": "中医科",
                "title": "主任医师",
                "specialty": "中医内科、养生保健",
                "introduction": "中医世家传人，擅长中医内科疑难杂症，在养生保健方面造诣深厚。",
                "is_recommended": 1,
            },
            {
                "name": "唐慧敏",
                "phone": "13900000072",
                "password": "doctor123",
                "department": "中医科",
                "title": "副主任医师",
                "specialty": "针灸推拿、康复理疗",
                "introduction": "针灸推拿专家，擅长颈椎病、腰椎病的中医治疗。",
                "is_recommended": 1,
            },
            {
                "name": "朱永康",
                "phone": "13900000073",
                "password": "doctor123",
                "department": "中医科",
                "title": "主治医师",
                "specialty": "中医妇科、调经助孕",
                "introduction": "擅长中医妇科疾病诊治，在调经助孕方面有丰富经验。",
                "is_recommended": 0,
            },
            {
                "name": "谢安平",
                "phone": "13900000074",
                "password": "doctor123",
                "department": "中医科",
                "title": "副主任医师",
                "specialty": "中医骨伤、正骨复位",
                "introduction": "中医骨伤科专家，擅长传统正骨手法和骨折康复。",
                "is_recommended": 1,
            },
        ]
        
        created_count = 0
        skipped_count = 0
        
        for doc_data in doctors_data:
            # 检查科室是否存在
            dept_name = doc_data["department"]
            if dept_name not in departments:
                print(f"⚠ 跳过医生 {doc_data['name']}: 科室 {dept_name} 不存在")
                skipped_count += 1
                continue
            
            result = await session.execute(select(Doctor).where(Doctor.phone == doc_data["phone"]))
            if not result.scalar_one_or_none():
                doctor = Doctor(
                    id=str(uuid.uuid4()),
                    name=doc_data["name"],
                    phone=doc_data["phone"],
                    password_hash=hash_password(doc_data["password"]),
                    department_id=departments[dept_name].id,
                    title=doc_data["title"],
                    specialty=doc_data["specialty"],
                    introduction=doc_data["introduction"],
                    is_recommended=doc_data["is_recommended"],
                    status=1
                )
                session.add(doctor)
                print(f"✓ 创建医生：{doc_data['name']} ({dept_name}) - {doc_data['phone']}")
                created_count += 1
            else:
                skipped_count += 1
        
        await session.commit()
        
        print(f"\n✅ 测试医生初始化完成!")
        print(f"   新创建: {created_count} 位医生")
        print(f"   已存在/跳过: {skipped_count} 位")
        print("\n医生登录信息:")
        print("  医生端: http://localhost:8003")
        print("  密码统一: doctor123")
        print("\n各科室医生手机号:")
        print("  内科:   13900000001-13900000004")
        print("  外科:   13900000011-13900000013")
        print("  儿科:   13900000021-13900000023")
        print("  妇产科: 13900000031-13900000033")
        print("  眼科:   13900000041-13900000043")
        print("  口腔科: 13900000051-13900000053")
        print("  皮肤科: 13900000061-13900000063")
        print("  中医科: 13900000071-13900000074")


if __name__ == "__main__":
    asyncio.run(init_doctors())
