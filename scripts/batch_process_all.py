import os
import requests
import time
import threading

# --- 认证与会话管理 ---

class AuthenticatedSession:
    """
    一个管理认证、Token刷新和API请求的会话类。
    """
    def __init__(self, base_url, auth_url, username, password):
        self.base_url = base_url
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self._lock = threading.Lock()

    def login(self):
        """使用用户名和密码登录，获取初始Token"""
        login_url = f"{self.auth_url}/auth/login"
        login_data = {"username_or_email": self.username, "password": self.password}
        print(f"[认证] 正在登录: {login_url}")
        try:
            resp = requests.post(login_url, json=login_data, timeout=10)
            if resp.status_code == 200:
                token_data = resp.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                print("[认证] 登录成功，已获取Token")
                return True
            else:
                print(f"[认证失败] 状态码: {resp.status_code}, 响应: {resp.text}")
                return False
        except Exception as e:
            print(f"[认证异常] 登录时发生错误: {e}")
            return False

    def _refresh_tokens(self):
        """使用Refresh Token获取新的Access Token和Refresh Token"""
        with self._lock:
            refresh_url = f"{self.auth_url}/auth/refresh"
            print("[认证] Access Token已过期或无效，正在刷新...")
            try:
                # The refresh endpoint expects a POST with the token in the body
                resp = requests.post(refresh_url, json={"refresh_token": self.refresh_token}, timeout=10)
                if resp.status_code == 200:
                    new_tokens = resp.json()
                    self.access_token = new_tokens.get("access_token")
                    self.refresh_token = new_tokens.get("refresh_token")
                    print("[认证] Token刷新成功")
                    return True
                else:
                    print(f"[认证失败] 刷新Token失败。状态码: {resp.status_code}, 响应: {resp.text}")
                    self.access_token = None
                    self.refresh_token = None
                    return False
            except Exception as e:
                print(f"[认证异常] 刷新Token时发生错误: {e}")
                return False

    def request(self, method, url, **kwargs):
        """
        发起一个带认证的请求，并在必要时自动刷新Token。
        """
        headers = kwargs.get("headers", {})
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs["headers"] = headers

        full_url = f"{self.base_url}{url}"
        
        # 第一次尝试
        try:
            resp = requests.request(method, full_url, **kwargs)
        except Exception as e:
            print(f"[请求异常] {method} {full_url}: {e}")
            raise

        # 如果是401，尝试刷新token并重试
        if resp.status_code == 401:
            print(f"[认证失败] {method} {full_url}: 收到401响应")
            if self.refresh_token:
                print("[认证] 尝试使用refresh token刷新...")
                if self._refresh_tokens():
                    # 更新header并重试
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    kwargs["headers"] = headers
                    print(f"[重试] 使用新Token再次请求: {method} {full_url}")
                    try:
                        resp = requests.request(method, full_url, **kwargs)
                        if resp.status_code == 401:
                            print(f"[认证失败] 刷新后仍然收到401，可能需要重新登录")
                    except Exception as e:
                        print(f"[重试异常] {e}")
                        raise
                else:
                    print("[认证失败] 刷新token失败，可能需要重新登录")
            else:
                print("[认证失败] 没有refresh token，无法自动刷新")
        
        return resp

# --- 认证配置 ---
AUTH_BASE_URL = "http://localhost:9001"
USERNAME = "shuaihao"
PASSWORD = "shuaihaopwd"
# --- 认证配置结束 ---

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = "/media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc1/model-code/data/2f685df1-0d89-4909-a8f3-d9bfa81a2d4d"
BASE_URL = "http://localhost:4200"


def wait_for_task(session: AuthenticatedSession, task_id: str, interval=5, timeout=3600):
    """轮询任务状态直到完成或超时"""
    url = f"/task_status/{task_id}"
    start = time.time()
    consecutive_failures = 0
    max_failures = 5  # 最多连续失败5次就退出
    
    while True:
        try:
            resp = session.request("GET", url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "")
                print(f"    [状态] {task_id}: {status}")
                consecutive_failures = 0  # 重置失败计数
                if status in ("completed", "failed", "error"):
                    return status
            elif resp.status_code == 401:
                print(f"    [认证失败] {task_id}: 状态码 {resp.status_code}, 尝试重新登录...")
                consecutive_failures += 1
                # 尝试重新登录
                if session.login():
                    print("    [认证] 重新登录成功，继续查询")
                    consecutive_failures = 0
                else:
                    print("    [认证] 重新登录失败")
                    if consecutive_failures >= max_failures:
                        return "auth_failed"
            else:
                print(f"    [查询失败] {task_id}: 状态码 {resp.status_code}, 响应: {resp.text}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"    [终止] {task_id}: 连续失败{consecutive_failures}次，停止查询")
                    return "query_failed"

        except Exception as e:
            print(f"    [查询异常] {e}")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                print(f"    [终止] {task_id}: 连续异常{consecutive_failures}次，停止查询")
                return "exception"

        if time.time() - start > timeout:
            print(f"    [超时] {task_id}")
            return "timeout"
        time.sleep(interval)

def trigger_all_process(sleep_sec=4):
    # --- 修改：使用会话对象 ---
    print("="*50)
    session = AuthenticatedSession(BASE_URL, AUTH_BASE_URL, USERNAME, PASSWORD)
    if not session.login():
        print("[错误] 登录失败，脚本终止。")
        return
    print("="*50)
    # --- 修改结束 ---

    for name in os.listdir(DATA_ROOT):
        folder = os.path.join(DATA_ROOT, name)
        if not os.path.isdir(folder):
            continue
        if "_" not in name:
            print(f"[跳过] 非标准命名: {name}")
            continue
        patient_name, study_date = name.split("_", 1)
        url = f"/process/{patient_name}/{study_date}"
        print(f"[提交] {session.base_url}{url}")
        try:
            resp = session.request("POST", url, timeout=60)
            resp_json = resp.json()
            print(f"  状态: {resp.status_code} {resp_json}")
            task_id = resp_json.get("task_id")
            if task_id:
                status = wait_for_task(session, task_id)
                print(f"  [完成] {task_id}: {status}")
            else:
                print("  [警告] 未返回 task_id")
        except Exception as e:
            print(f"  错误: {e}")
        time.sleep(sleep_sec)  # 防止压力过大

if __name__ == "__main__":
    trigger_all_process()