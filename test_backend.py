#!/usr/bin/env python3
"""
测试后台任务 API 的脚本
"""
import requests
import time
import json

BASE_URL = "http://localhost:4200"

def test_continue_after_l3(patient_name, study_date):
    """测试 continue_after_l3 后台任务"""
    print(f"\n{'='*60}")
    print(f"测试 continue_after_l3: {patient_name}_{study_date}")
    print(f"{'='*60}\n")
    
    # 1. 提交任务
    url = f"{BASE_URL}/continue_after_l3/{patient_name}/{study_date}"
    print(f"[1] 提交任务: POST {url}")
    response = requests.post(url)
    print(f"    响应状态: {response.status_code}")
    print(f"    响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
    
    if response.status_code != 200:
        print("❌ 提交任务失败")
        return
    
    result = response.json()
    task_id = result.get("task_id")
    
    if not task_id:
        print("❌ 未返回 task_id")
        return
    
    # 2. 轮询任务状态
    print(f"[2] 轮询任务状态: {task_id}")
    max_attempts = 60  # 最多轮询 60 次
    for i in range(max_attempts):
        time.sleep(5)  # 每 5 秒查询一次
        
        status_url = f"{BASE_URL}/task_status/{task_id}"
        status_response = requests.get(status_url)
        
        if status_response.status_code != 200:
            print(f"    ⚠️  查询失败: {status_response.status_code}")
            continue
        
        status = status_response.json()
        status_str = status.get("status", "unknown")
        progress = status.get("progress", 0)
        message = status.get("message", "")
        
        print(f"    [{i+1}/{max_attempts}] 状态: {status_str} | 进度: {progress}% | {message}")
        
        if status_str == "completed":
            print(f"\n✅ 任务完成!")
            print(f"    结果: {json.dumps(status.get('result', {}), indent=2, ensure_ascii=False)}")
            break
        elif status_str == "failed":
            print(f"\n❌ 任务失败!")
            print(f"    错误: {status.get('error', 'Unknown error')}")
            break
    else:
        print(f"\n⚠️  超时: 轮询 {max_attempts} 次后仍未完成")

def test_list_tasks():
    """列出所有任务"""
    print(f"\n{'='*60}")
    print("列出所有任务")
    print(f"{'='*60}\n")
    
    url = f"{BASE_URL}/list_tasks"
    response = requests.get(url)
    print(f"响应状态: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  {sys.argv[0]} <patient_name> <study_date>")
        print(f"  {sys.argv[0]} list")
        print("\n示例:")
        print(f"  {sys.argv[0]} 613100 20250929")
        print(f"  {sys.argv[0]} list")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        test_list_tasks()
    else:
        if len(sys.argv) < 3:
            print("❌ 缺少参数: study_date")
            sys.exit(1)
        patient_name = sys.argv[1]
        study_date = sys.argv[2]
        test_continue_after_l3(patient_name, study_date)
