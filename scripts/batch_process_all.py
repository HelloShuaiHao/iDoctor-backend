import os
import requests
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
BASE_URL = "http://localhost:4200"

def wait_for_task(task_id, interval=5, timeout=3600):
    """轮询任务状态直到完成或超时"""
    url = f"{BASE_URL}/task_status/{task_id}"
    start = time.time()
    while True:
        try:
            resp = requests.get(url, timeout=10)
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
            resp = requests.post(url, timeout=60)
            resp_json = resp.json()
            print(f"  状态: {resp.status_code} {resp_json}")
            task_id = resp_json.get("task_id")
            if task_id:
                status = wait_for_task(task_id)
                print(f"  [完成] {task_id}: {status}")
            else:
                print("  [警告] 未返回 task_id")
        except Exception as e:
            print(f"  错误: {e}")
        time.sleep(sleep_sec)  # 防止压力过大

if __name__ == "__main__":
    trigger_all_process()