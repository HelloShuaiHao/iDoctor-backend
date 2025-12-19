import os
import requests
import time

# --- 新增：认证配置 ---
AUTH_BASE_URL = "http://localhost:9001"
USERNAME = "shuaihao"
PASSWORD = "shuaihaopwd"
# --- 认证配置结束 ---

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = "/media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc/model-code/data/2f685df1-0d89-4909-a8f3-d9bfa81a2d4d"
BASE_URL = "http://localhost:4200"

# --- 新增：登录并获取Token的函数 ---
def login_and_get_token():
    """使用用户名和密码登录，获取JWT Token"""
    login_url = f"{AUTH_BASE_URL}/auth/login"
    login_data = {
        "username_or_email": USERNAME,
        "password": PASSWORD
    }
    print(f"[认证] 正在登录: {login_url}")
    try:
        resp = requests.post(login_url, json=login_data, timeout=10)
        if resp.status_code == 200:
            token_data = resp.json()
            access_token = token_data.get("access_token")
            print("[认证] 登录成功，已获取Token")
            return access_token
        else:
            print(f"[认证失败] 状态码: {resp.status_code}, 响应: {resp.text}")
            return None
    except Exception as e:
        print(f"[认证异常] 登录时发生错误: {e}")
        return None
# --- 函数结束 ---

def wait_for_task(task_id, headers, interval=5, timeout=3600):
    """轮询任务状态直到完成或超时"""
    url = f"{BASE_URL}/task_status/{task_id}"
    start = time.time()
    while True:
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            data = resp.json()
            status = data.get("status", "")
            print(f"    [状态] {task_id}: {status}")
            if status in ("completed", "failed", "error"):
                return status
        except Exception as e:
            print(f"    [查询异常] {e}")
        if time.time() - start > timeout:
            print(f"    [超时] {task_id}")
            return "timeout"
        time.sleep(interval)

def trigger_all_process(sleep_sec=4):
    # --- 修改：在开始时获取Token ---
    print("="*50)
    token = login_and_get_token()
    if not token:
        print("[错误] 未能获取认证Token，脚本终止。")
        return
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
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
        url = f"{BASE_URL}/process/{patient_name}/{study_date}"
        print(f"[提交] {url}")
        try:
            resp = requests.post(url, timeout=60, headers=headers)
            resp_json = resp.json()
            print(f"  状态: {resp.status_code} {resp_json}")
            task_id = resp_json.get("task_id")
            if task_id:
                status = wait_for_task(task_id, headers)
                print(f"  [完成] {task_id}: {status}")
            else:
                print("  [警告] 未返回 task_id")
        except Exception as e:
            print(f"  错误: {e}")
        time.sleep(sleep_sec)  # 防止压力过大

if __name__ == "__main__":
    trigger_all_process()