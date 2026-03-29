"""
Locust 性能测试 —— 医院预约挂号系统核心接口。

使用方式::

    # 在 apps/server 目录下运行
    cd apps/server
    pip install locust

    # Web UI 模式（浏览器打开 http://localhost:8089）
    locust -f tests/perf/locustfile.py --host http://localhost:8000

    # 无头模式（适合 CI）
    locust -f tests/perf/locustfile.py \
        --host http://localhost:8000 \
        --headless \
        --users 50 --spawn-rate 5 --run-time 60s

场景说明：
    - LoginUser:       权重 1，模拟管理员登录获取 token
    - ListAppointments: 权重 3，查询预约列表（需登录）
    - ListSchedules:    权重 2，查询排班列表（需登录）
    - ListDoctors:      权重 4，查询医生列表（需登录）
"""

from locust import FastHttpUser, task, between, events
from tests.perf.config import (
    LOGIN_PHONE,
    LOGIN_PASSWORD,
    TENANT_ID,
)

# ---------------------------------------------------------------------------
# 公共常量
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"


class _AuthenticatedUser(FastHttpUser):
    """已认证用户的公共基类，处理登录和 token 刷新。"""

    # 请求间隔 1-3 秒，模拟真实用户浏览行为
    wait_time = between(1, 3)

    # 连接池优化
    connection_timeout = 10.0
    network_timeout = 10.0
    max_retries = 1
    insecure = True  # 跳过 SSL 验证（测试环境）

    def _build_headers(self, token: str | None = None) -> dict:
        """构建请求头，包含租户上下文和认证信息。"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if TENANT_ID:
            headers["X-Tenant-ID"] = TENANT_ID
        return headers

    def _login(self) -> str | None:
        """执行登录并返回 access_token，失败返回 None。"""
        headers = self._build_headers()
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"phone": LOGIN_PHONE, "password": LOGIN_PASSWORD},
            headers=headers,
            name="/api/v1/auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                # 统一响应格式: {"code": 0, "data": {"access_token": ...}}
                data = body.get("data", body)
                token = data.get("access_token")
                if token:
                    resp.success()
                    return token
            resp.failure(f"Login failed: status={resp.status_code}")
            return None

    def on_start(self) -> None:
        """每个虚拟用户启动时自动登录。"""
        self.token: str | None = self._login()


# ---------------------------------------------------------------------------
# 测试场景
# ---------------------------------------------------------------------------

class LoginUser(FastHttpUser):
    """
    登录场景 —— 模拟管理员反复登录。
    权重 1：登录频率最低（真实场景中用户不会频繁登录）。
    """

    weight = 1
    wait_time = between(1, 3)

    connection_timeout = 10.0
    network_timeout = 10.0
    max_retries = 1
    insecure = True

    def _build_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if TENANT_ID:
            headers["X-Tenant-ID"] = TENANT_ID
        return headers

    @task
    def login(self):
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"phone": LOGIN_PHONE, "password": LOGIN_PASSWORD},
            headers=self._build_headers(),
            name="/api/v1/auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data", body)
                if data.get("access_token"):
                    resp.success()
                    return
            resp.failure(f"Login failed: status={resp.status_code}")


class ListAppointments(_AuthenticatedUser):
    """
    预约列表查询场景。
    权重 3：中等频率（管理后台核心操作）。
    """

    weight = 3

    @task
    def list_appointments(self):
        params = {"page": 1, "page_size": 10}
        with self.client.get(
            f"{API_PREFIX}/appointments",
            params=params,
            headers=self._build_headers(self.token),
            name="/api/v1/appointments",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                # token 过期，重新登录
                self.token = self._login()
                resp.failure("Token expired, re-login")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


class ListSchedules(_AuthenticatedUser):
    """
    排班列表查询场景。
    权重 2：中等偏低频率（排班查看不如预约频繁）。
    """

    weight = 2

    @task
    def list_schedules(self):
        params = {"page": 1, "page_size": 10}
        with self.client.get(
            f"{API_PREFIX}/schedules",
            params=params,
            headers=self._build_headers(self.token),
            name="/api/v1/schedules",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired, re-login")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


class ListDoctors(_AuthenticatedUser):
    """
    医生列表查询场景。
    权重 4：高频（多个页面都依赖医生列表数据）。
    """

    weight = 4

    @task
    def list_doctors(self):
        params = {"page": 1, "page_size": 10}
        with self.client.get(
            f"{API_PREFIX}/doctors",
            params=params,
            headers=self._build_headers(self.token),
            name="/api/v1/doctors",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired, re-login")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")
