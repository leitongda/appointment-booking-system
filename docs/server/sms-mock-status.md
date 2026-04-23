# SMS Mock 状态文档

## 当前实现状态

**当前状态：Mock 模式（仅开发环境）**

短信服务位于 `apps/server/app/infrastructure/sms/service.py`，目前仅支持 console 输出模拟发送，**未接入真实短信服务商 SDK**。

### 实现细节

1. **验证码生成与存储**
   - 支持租户隔离（Redis key 带租户前缀）
   - 验证码有效期：5 分钟（300 秒）
   - 发送间隔限制：60 秒防刷

2. **当前发送行为（Mock）**
   ```python
   # 当前仅打印到控制台
   logger.info(f"[SMS] 向 {phone} 发送{code_type}验证码: {code}")
   print(f"📱 短信验证码\n手机号: {phone}\n验证码: {code}...")
   ```

3. **日志记录**
   - 所有发送尝试都会记录到 `notification_logs` 表
   - 包含发送状态（sent/failed）、错误信息等

## 依赖 SMS 的业务流程

### 1. 管理员短信验证码登录
- **路由**: `POST /api/v1/admin/auth/sms/send` 和 `/api/v1/admin/auth/sms/login`
- **文件**: `apps/server/app/modules/admin/router_auth_login.py`
- **用途**: 管理员使用手机号 + 验证码登录

### 2. 潜在扩展场景
- 患者端手机验证（未来可能需要）
- 预约提醒通知（目前未实现）
- 取消预约通知（目前未实现）

## 接入真实 SDK 需要的配置

### 阿里云短信服务

**环境变量需求**:
```bash
SMS_PROVIDER=aliyun
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
SMS_SIGN_NAME=your_sign_name
SMS_TEMPLATE_CODE=your_template_code
```

**依赖安装**:
```bash
pip install alibabacloud_dysmsapi20170525
```

**代码已预留**: `_send_aliyun()` 方法（已注释），需取消注释并完成实现

### 腾讯云短信服务

**环境变量需求**:
```bash
SMS_PROVIDER=tencent
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
SMS_SDK_APP_ID=your_app_id
SMS_SIGN_NAME=your_sign_name
SMS_TEMPLATE_ID=your_template_id
```

**依赖安装**:
```bash
pip install tencentcloud-sdk-python
```

**代码已预留**: `_send_tencent()` 方法（已注释），需取消注释并完成实现

## 建议的 Provider Adapter 接口设计

为了方便切换不同短信服务商，建议采用适配器模式：

```python
# infrastructure/sms/base.py
from abc import ABC, abstractmethod

class SmsProvider(ABC):
    @abstractmethod
    async def send_verification_code(self, phone: str, code: str, template_params: dict) -> bool:
        pass

# infrastructure/sms/aliyun_provider.py
class AliyunSmsProvider(SmsProvider):
    async def send_verification_code(self, phone: str, code: str, template_params: dict) -> bool:
        # 阿里云实现
        pass

# infrastructure/sms/tencent_provider.py
class TencentSmsProvider(SmsProvider):
    async def send_verification_code(self, phone: str, code: str, template_params: dict) -> bool:
        # 腾讯云实现
        pass

# infrastructure/sms/factory.py
def get_sms_provider() -> SmsProvider:
    provider = settings.SMS_PROVIDER
    if provider == 'aliyun':
        return AliyunSmsProvider()
    elif provider == 'tencent':
        return TencentSmsProvider()
    else:
        return MockSmsProvider()  # 开发环境默认
```

### 优势

1. **解耦**: 业务代码与具体服务商无关
2. **可测试性**: 方便注入 mock provider 进行单元测试
3. **可扩展性**: 新增服务商只需实现接口
4. **配置驱动**: 通过环境变量切换服务商

## 迁移建议

1. **阶段一**: 选择一个服务商（推荐阿里云，市场占有率高）
2. **阶段二**: 实现对应的 provider，添加单元测试
3. **阶段三**: 在 `.env` 中配置真实凭证，在 staging 环境验证
4. **阶段四**: 生产环境切换，关闭 mock 模式

## 注意事项

- **成本控制**: 短信发送有费用，需要添加发送量监控和预算告警
- **限流保护**: 当前已有 60 秒发送间隔，建议添加日/月发送量上限
- **模板审核**: 短信模板需要服务商审核，提前准备
- **多租户隔离**: 不同租户可能需要不同的签名/模板，需要在配置中支持
