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

    # 高并发压测
    locust -f tests/perf/locustfile.py \
        --host http://localhost:8000 \
        --headless \
        --users 500 --spawn-rate 20 --run-time 120s

场景说明：
    - LoginUser:           权重 1，模拟管理员登录获取 token
    - ListAppointments:    权重 3，查询预约列表（需登录）
    - ListSchedules:       权重 2，查询排班列表（需登录）
    - ListDoctors:         权重 4，查询医生列表（需登录）
    - PatientBookingFlow:  权重 5，患者端挂号流程（浏览→选医生→选号源→预约）
    - AdminCheckinFlow:    权重 2，管理员签到流程（查预约→签到）
    - AdminCancelFlow:     权重 1，管理员取消流程（查预约→取消）
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
# 测试场景：读操作
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


# ---------------------------------------------------------------------------
# 测试场景：写操作（核心业务流程）
# ---------------------------------------------------------------------------

class PatientBookingFlow(_AuthenticatedUser):
    """
    患者端挂号流程 —— 模拟真实挂号场景。

    流程：浏览医生 → 查看排班 → 创建预约
    权重 5：最高频（挂号是系统核心功能）
    """

    weight = 5

    @task(3)
    def browse_doctors(self):
        """浏览医生列表（高频，多个页面依赖）"""
        params = {"page": 1, "page_size": 20}
        with self.client.get(
            f"{API_PREFIX}/doctors",
            params=params,
            headers=self._build_headers(self.token),
            name="/api/v1/doctors [booking-flow]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired")
            else:
                resp.failure(f"Status: {resp.status_code}")

    @task(2)
    def check_schedules(self):
        """查看排班（中频，选择号源前必看）"""
        params = {"page": 1, "page_size": 10}
        with self.client.get(
            f"{API_PREFIX}/schedules",
            params=params,
            headers=self._build_headers(self.token),
            name="/api/v1/schedules [booking-flow]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired")
            else:
                resp.failure(f"Status: {resp.status_code}")

    @task(1)
    def create_appointment(self):
        """创建预约（低频但关键，写操作）"""
        # 注意：实际预约需要真实的 schedule_id 和 patient_id
        # 这里用占位数据测试 API 响应，真实压测需配置测试数据
        payload = {
            "schedule_id": "test-schedule-id",
            "patient_id": "test-patient-id",
            "symptoms": "压测自动生成",
        }
        with self.client.post(
            f"{API_PREFIX}/appointments",
            json=payload,
            headers=self._build_headers(self.token),
            name="/api/v1/appointments [create]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired")
            elif resp.status_code == 400:
                # 业务错误（如号源已满）是预期行为
                resp.success()
            else:
                resp.failure(f"Status: {resp.status_code}")


class AdminCheckinFlow(_AuthenticatedUser):
    """
    管理员签到流程 —— 模拟现场签到场景。

    流程：查预约列表 → 签到
    权重 2：中频（现场签到操作）
    """

    weight = 2

    @task(2)
    def list_confirmed(self):
        """查询待签到预约"""
        params = {"page": 1, "page_size": 10, "status": 1}  # 1=CONFIRMED
        with self.client.get(
            f"{API_PREFIX}/appointments",
            params=params,
            headers=self._build_headers(self.token),
            name="/api/v1/appointments [checkin-list]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired")
            else:
                resp.failure(f"Status: {resp.status_code}")

    @task(1)
    def checkin_appointment(self):
        """签到（写操作）"""
        # 注意：实际签到需要真实的 appointment_id
        appointment_id = "test-appointment-id"
        with self.client.post(
            f"{API_PREFIX}/appointments/{appointment_id}/checkin",
            json={"checkin_method": "MANUAL"},
            headers=self._build_headers(self.token),
            name="/api/v1/appointments/{id}/checkin",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired")
            elif resp.status_code == 400:
                # 业务错误（如已签到）是预期行为
                resp.success()
            else:
                resp.failure(f"Status: {resp.status_code}")


class AdminCancelFlow(_AuthenticatedUser):
    """
    管理员取消流程 —— 模拟取消预约场景。

    流程：查预约 → 取消
    权重 1：低频（取消操作不常见）
    """

    weight = 1

    @task(1)
    def cancel_appointment(self):
        """取消预约（写操作）"""
        # 注意：实际取消需要真实的 appointment_id
        appointment_id = "test-appointment-id"
        with self.client.post(
            f"{API_PREFIX}/appointments/{appointment_id}/cancel",
            json={"reason": "压测自动取消"},
            headers=self._build_headers(self.token),
            name="/api/v1/appointments/{id}/cancel",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self.token = self._login()
                resp.failure("Token expired")
            elif resp.status_code == 400:
                # 业务错误（如已取消）是预期行为
                resp.success()
            else:
                resp.failure(f"Status: {resp.status_code}")
