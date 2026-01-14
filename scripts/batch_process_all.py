import os
import sys
import time
import multiprocessing
import signal

# 添加项目根目录到Python路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 导入处理函数
from all_new import main  # 主处理函数在all_new.py中

DATA_ROOT = os.path.join(PROJECT_ROOT, "data", "2f685df1-0d89-4909-a8f3-d9bfa81a2d4d")

def process_single_patient(input_folder, output_folder, result_queue):
    """单独进程处理单个患者，将结果放入队列"""
    try:
        main(input_folder, output_folder)
        result_queue.put(("success", "处理完成"))
    except Exception as e:
        result_queue.put(("failed", str(e)))

def process_all_patients(timeout_minutes=2):
    """直接调用处理函数处理所有患者数据，带超时保护"""
    print("="*50)
    print("开始批量处理所有患者数据")
    print(f"数据根目录: {DATA_ROOT}")
    print(f"单个患者超时时间: {timeout_minutes} 分钟")
    print("="*50)
    
    if not os.path.exists(DATA_ROOT):
        print(f"[错误] 数据根目录不存在: {DATA_ROOT}")
        return
        
    patient_folders = []
    for name in os.listdir(DATA_ROOT):
        folder = os.path.join(DATA_ROOT, name)
        if not os.path.isdir(folder):
            continue
        if "_" not in name:
            print(f"[跳过] 非标准命名: {name}")
            continue
        patient_folders.append(name)
    
    print(f"[发现] 共找到 {len(patient_folders)} 个患者文件夹")
    
    success_count = 0
    failed_count = 0
    timeout_count = 0
    timeout_seconds = timeout_minutes * 60
    
    for i, folder_name in enumerate(patient_folders, 1):
        print(f"\n[{i}/{len(patient_folders)}] 正在处理: {folder_name}")
        
        patient_name, study_date = folder_name.split("_", 1)
        patient_folder = os.path.join(DATA_ROOT, folder_name)
        input_folder = os.path.join(patient_folder, "input")
        output_folder = os.path.join(patient_folder, "output")
        
        # 检查input文件夹是否存在
        if not os.path.exists(input_folder):
            print(f"  [跳过] input文件夹不存在: {input_folder}")
            failed_count += 1
            continue
            
        # 创建output文件夹
        os.makedirs(output_folder, exist_ok=True)
        
        start_time = time.time()
        print(f"  [开始] 输入: {input_folder}")
        print(f"  [开始] 输出: {output_folder}")
        print(f"  [超时] 最大等待时间: {timeout_minutes} 分钟")
        
        # 使用multiprocessing创建子进程处理
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=process_single_patient, 
            args=(input_folder, output_folder, result_queue)
        )
        
        try:
            process.start()
            process.join(timeout=timeout_seconds)  # 等待指定时间
            
            if process.is_alive():
                # 进程仍在运行，说明超时了
                print(f"  [超时] 处理时间超过 {timeout_minutes} 分钟，强制终止")
                process.terminate()
                process.join(timeout=5)  # 等待5秒让进程优雅退出
                
                if process.is_alive():
                    # 如果还活着，强制杀死
                    print(f"  [强杀] 进程无法优雅退出，强制杀死")
                    process.kill()
                    process.join()
                
                timeout_count += 1
                elapsed = time.time() - start_time
                print(f"  [失败] 超时终止，已运行: {elapsed:.2f}秒")
                
            else:
                # 进程正常退出，检查结果
                elapsed = time.time() - start_time
                
                try:
                    status, message = result_queue.get_nowait()
                    if status == "success":
                        print(f"  [完成] 耗时: {elapsed:.2f}秒")
                        success_count += 1
                    else:
                        print(f"  [失败] 处理异常: {message}")
                        print(f"  [失败] 耗时: {elapsed:.2f}秒")
                        failed_count += 1
                except:
                    # 队列为空或其他异常
                    print(f"  [异常] 进程结束但无法获取结果")
                    failed_count += 1
                    
        except Exception as e:
            print(f"  [异常] 启动处理进程失败: {e}")
            failed_count += 1
        finally:
            # 确保进程被清理
            if process.is_alive():
                process.terminate()
                process.join()
    
    print("\n" + "="*50)
    print("批量处理完成")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"超时: {timeout_count}")
    print(f"总计: {len(patient_folders)}")
    print("="*50)

if __name__ == "__main__":
    # 可以自定义超时时间（分钟），默认2分钟
    process_all_patients(timeout_minutes=2)