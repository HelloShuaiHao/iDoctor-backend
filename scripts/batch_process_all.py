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
                # 后端期望refresh_token作为查询参数，不是request body
                refresh_url_with_token = f"{refresh_url}?refresh_token={self.refresh_token}"
                resp = requests.post(refresh_url_with_token, timeout=10)
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
    processing_count = 0  # 连续processing状态的计数
    max_processing = 20   # 如果连续processing超过100次（约8分钟），强制检查
    
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
                elif status == "processing":
                    processing_count += 1
                    if processing_count > max_processing:
                        print(f"    [警告] {task_id}: 连续processing {processing_count}次，可能状态更新有问题")
                        # 检查一下是否真的完成了但状态没有更新
                        print(f"    [检查] {task_id}: 查询所有任务状态进行对比...")
                        try:
                            list_resp = session.request("GET", "/list_tasks", timeout=10)
                            if list_resp.status_code == 200:
                                all_tasks = list_resp.json()
                                current_task = all_tasks.get("tasks", {}).get(task_id, {})
                                print(f"    [对比] {task_id}: 从/list_tasks获取的状态: {current_task.get('status', 'unknown')}")
                                if current_task.get("status") in ("completed", "failed", "error"):
                                    print(f"    [发现] {task_id}: 任务实际已完成，但/task_status接口返回错误状态")
                                    return current_task.get("status", "completed")
                        except Exception as e:
                            print(f"    [检查异常] {e}")
                        
                        # 如果长期processing，可以选择返回timeout或继续等待
                        return "stuck_processing"
                else:
                    processing_count = 0  # 重置processing计数
                    
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

        elapsed = time.time() - start
        if elapsed > timeout:
            print(f"    [超时] {task_id}: 已等待 {elapsed:.0f} 秒")
            return "timeout"
            
        # 显示已等待时间，每分钟显示一次
        if int(elapsed) % 60 == 0 and elapsed > 0:
            print(f"    [等待中] {task_id}: 已等待 {elapsed:.0f} 秒, 状态: {status if 'status' in locals() else 'unknown'}")
            
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
                print(f"  [开始等待] {task_id}: 开始状态轮询...")
                status = wait_for_task(session, task_id)
                print(f"  [完成] {task_id}: {status}")
                
                # 如果是stuck状态，尝试获取所有任务列表进行调试
                if status in ("stuck_processing", "timeout"):
                    print(f"  [调试] 获取所有任务状态...")
                    try:
                        list_resp = session.request("GET", "/list_tasks", timeout=10)
                        if list_resp.status_code == 200:
                            all_tasks = list_resp.json()
                            current_task = all_tasks.get("tasks", {}).get(task_id, {})
                            print(f"  [调试] 当前任务实际状态: {current_task}")
                        else:
                            print(f"  [调试] 无法获取任务列表: {list_resp.status_code}")
                    except Exception as e:
                        print(f"  [调试] 获取任务列表异常: {e}")
            else:
                print("  [警告] 未返回 task_id")
        except Exception as e:
            print(f"  错误: {e}")
        time.sleep(sleep_sec)  # 防止压力过大

if __name__ == "__main__":
    trigger_all_process()