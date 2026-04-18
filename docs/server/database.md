# 🗄️ 数据库操作

## 概述

数据库模块使用 SQLAlchemy 2.0 异步模式，位于 `app/db/` 目录：

- `base.py` - 基础模型类
- `session.py` - 会话管理和连接池

---

## 连接配置

### 环境变量

```env
DATABASE_URL=postgresql+asyncpg://hospital:hospital123@localhost:5432/hospital_booking
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

### 连接池参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pool_size` | 10 | 连接池保持的连接数 |
| `max_overflow` | 20 | 超出 pool_size 后可创建的最大连接数 |
| `pool_timeout` | 30 | 获取连接的超时时间（秒） |
| `pool_recycle` | 1800 | 连接回收时间（秒），防止断连 |
| `pool_pre_ping` | True | 使用前检查连接是否有效 |

---

## 获取数据库会话

### 依赖注入（推荐）

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

### 上下文管理器

```python
from app.db.session import async_session_maker

async def background_task():
    async with async_session_maker() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        # 处理数据
```

---

## 模型定义

### 基础模型

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 定义模型

```python
# app/models/user.py
from sqlalchemy import Column, String, Integer, Boolean
from app.db.base import Base, TimestampMixin
import uuid

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, index=True)
    nickname = Column(String(50))
    avatar = Column(String(500))
    gender = Column(Integer, default=0)  # 0-未知 1-男 2-女
    status = Column(Integer, default=1)  # 1-正常 0-禁用
```

### 关联关系

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    department_id = Column(String(36), ForeignKey("departments.id"))
    
    # 关联
    user = relationship("User", backref="doctor")
    department = relationship("Department", backref="doctors")
```

---

## CRUD 操作

### 查询单个

```python
from sqlalchemy import select

# 按 ID 查询
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()

# 按条件查询
result = await db.execute(select(User).where(User.phone == phone))
user = result.scalar_one_or_none()
```

### 查询列表

```python
# 查询所有
result = await db.execute(select(User))
users = result.scalars().all()

# 带条件查询
result = await db.execute(
    select(User)
    .where(User.status == 1)
    .order_by(User.created_at.desc())
    .limit(10)
    .offset(0)
)
users = result.scalars().all()
```

### 分页查询

```python
from sqlalchemy import func

# 查询总数
count_result = await db.execute(select(func.count(User.id)).where(User.status == 1))
total = count_result.scalar()

# 查询分页数据
result = await db.execute(
    select(User)
    .where(User.status == 1)
    .order_by(User.created_at.desc())
    .limit(page_size)
    .offset((page - 1) * page_size)
)
users = result.scalars().all()
```

### 创建

```python
# 创建单个
user = User(phone="13800138000", nickname="张三")
db.add(user)
await db.commit()
await db.refresh(user)  # 刷新获取自动生成的字段

# 批量创建
users = [User(phone=f"138{i:08d}") for i in range(100)]
db.add_all(users)
await db.commit()
```

### 更新

```python
# 方式1: 查询后更新
user = await db.get(User, user_id)
if user:
    user.nickname = "新昵称"
    user.updated_at = datetime.utcnow()
    await db.commit()

# 方式2: 直接更新（推荐，性能更好）
from sqlalchemy import update

await db.execute(
    update(User)
    .where(User.id == user_id)
    .values(nickname="新昵称", updated_at=datetime.utcnow())
)
await db.commit()
```

### 删除

```python
# 方式1: 查询后删除
user = await db.get(User, user_id)
if user:
    await db.delete(user)
    await db.commit()

# 方式2: 直接删除
from sqlalchemy import delete

await db.execute(delete(User).where(User.id == user_id))
await db.commit()
```

---

## 复杂查询

### 多表关联

```python
from sqlalchemy.orm import selectinload, joinedload

# 预加载关联（推荐，避免 N+1 问题）
result = await db.execute(
    select(Doctor)
    .options(selectinload(Doctor.department))
    .where(Doctor.status == 1)
)
doctors = result.scalars().all()

# 访问关联数据（已预加载，不会额外查询）
for doctor in doctors:
    print(doctor.department.name)
```

### JOIN 查询

```python
from sqlalchemy import and_, or_

result = await db.execute(
    select(Appointment, Doctor, Schedule)
    .join(Doctor, Appointment.doctor_id == Doctor.id)
    .join(Schedule, Appointment.schedule_id == Schedule.id)
    .where(
        and_(
            Appointment.user_id == user_id,
            Appointment.status.in_([1, 2, 4])  # 已预约、已签到、就诊中
        )
    )
)
rows = result.all()

for appointment, doctor, schedule in rows:
    print(f"{doctor.name} - {schedule.schedule_date}")
```

### 聚合查询

```python
from sqlalchemy import func

# 统计数量
result = await db.execute(
    select(func.count(Appointment.id))
    .where(Appointment.status == 1)
)
count = result.scalar()

# 分组统计
result = await db.execute(
    select(
        Appointment.status,
        func.count(Appointment.id).label("count")
    )
    .group_by(Appointment.status)
)
stats = result.all()
# [(1, 100), (2, 50), (3, 30)]
```

---

## 事务处理

### 自动提交

```python
async def create_appointment(db: AsyncSession, data: dict):
    appointment = Appointment(**data)
    db.add(appointment)
    await db.commit()  # 提交事务
    await db.refresh(appointment)
    return appointment
```

### 手动事务

```python
async def transfer_points(db: AsyncSession, from_user: str, to_user: str, points: int):
    try:
        # 扣减积分
        await db.execute(
            update(User)
            .where(User.id == from_user)
            .values(points=User.points - points)
        )
        
        # 增加积分
        await db.execute(
            update(User)
            .where(User.id == to_user)
            .values(points=User.points + points)
        )
        
        await db.commit()
    except Exception as e:
        await db.rollback()  # 回滚事务
        raise
```

### 嵌套事务（Savepoint）

```python
from sqlalchemy import text

async def complex_operation(db: AsyncSession):
    # 开始事务
    await db.execute(text("SAVEPOINT sp1"))
    
    try:
        # 操作 1
        await do_something(db)
        
        await db.execute(text("SAVEPOINT sp2"))
        try:
            # 操作 2（可能失败）
            await do_risky_thing(db)
        except Exception:
            await db.execute(text("ROLLBACK TO SAVEPOINT sp2"))
            # 继续执行其他操作
        
        await db.commit()
    except Exception:
        await db.execute(text("ROLLBACK TO SAVEPOINT sp1"))
        raise
```

---

## 数据库迁移

使用 Alembic 管理数据库迁移：

```bash
# 创建迁移
alembic revision --autogenerate -m "add user table"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history
```

---

## 最佳实践

1. **使用依赖注入**：在 API 中使用 `Depends(get_db)` 获取会话
2. **预加载关联**：使用 `selectinload` 避免 N+1 问题
3. **批量操作**：大量数据使用 `add_all` 或批量 `update/delete`
4. **事务管理**：确保操作的原子性，异常时回滚
5. **连接池**：合理配置连接池参数，避免连接耗尽
6. **索引优化**：为常用查询字段添加索引
