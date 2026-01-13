# FastAPI + nnUNet 服务器崩溃问题修复报告

## 问题描述

在使用 FastAPI 部署包含 nnUNet 医学图像分割模型的服务时，服务器在处理 `/continue_after_l3` 接口时会意外崩溃，日志显示：
- `asyncio.exceptions.CancelledError`
- `terminate called without an active exception`
- `INFO: Shutting down`

## 问题分析过程

### 1. 初步排查

**现象：**
- 服务器在 `continue_after_l3` 函数执行过程中自动关闭
- `run_psoas_pipeline` (detectron2) 阶段完成
- 进入 `run_nnunet_predict_and_overlay` (nnUNet) 阶段后服务器立即崩溃

### 2. 定位原因

经过逐步排查，发现主要问题：

#### **问题一：nnUNet 多进程与 FastAPI 事件循环冲突**

**位置：** `seg.py` 中的 `run_nnunet_predict_and_overlay` 函数

nnUNet 的 `predict_from_files` 方法默认使用多进程进行预处理和导出：
- `num_processes_preprocessing=8`（默认）- 预处理阶段
- `num_processes_segmentation_export=8`（默认）- 导出阶段

这些进程使用 `multiprocessing.get_context('spawn')` 创建，会与 FastAPI 的 asyncio 事件循环产生冲突。

#### **问题二：C++ 线程安全问题**

**现象：** `terminate called without an active exception`

这是一个 C++ 运行时错误，通常发生在：
- C++ 线程被不正确地终止
- PyTorch 的 CUDA 操作与 Python 线程有竞争条件
- 资源未正确释放导致的状态残留

### 3. 解决方案

#### **方案一：使用 nnUNet 顺序处理模式**

修改 `seg.py`，使用 `predict_from_files_sequential` 替代 `predict_from_files`：

```python
# seg.py
def run_nnunet_predict_and_overlay(input_dir: str, output_dir: str, model_dir: str, checkpoint: str = "checkpoint_final.pth"):
    # ...
    predictor.predict_from_files_sequential(
        input_dir,
        output_dir,
        save_probabilities=False,
    )
```

**优点：** 完全避免了 nnUNet 的多进程机制

#### **方案二：限制底层 C++ 多线程**

在 `app.py` 中添加环境变量限制：

```python
# app.py 顶部
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import torch
torch.set_num_threads(1)
```

**作用：** 限制 PyTorch、OpenMP、MKL 等底层库只使用单线程，避免线程竞争

#### **方案三：使用子进程完全隔离**

**核心方案！** 每次处理都在独立的子进程中运行，完全隔离状态：

```python
# app.py 中的后台任务实现
import subprocess
import threading

def run_in_subprocess():
    cmd = [
        "python", "-c",
        f"""
import os, sys
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
sys.path.insert(0, "{os.getcwd()}")
from all_new import continue_after_l3
result = continue_after_l3("{input_folder}", "{output_folder}")
print("SUBPROCESS_RESULT:", result)
"""
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=os.getcwd()
    )

    # 实时读取输出
    result_line = None
    for line in proc.stdout:
        print(f"[子进程] {line.rstrip()}")
        if line.startswith("SUBPROCESS_RESULT:"):
            result_line = line

    proc.wait()
    # 处理结果...
```

## 最终解决方案

**采用方案三（子进程隔离）+ 方案二（限制线程）**

### 修改后的核心文件

#### 1. `/media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc2/model-code/seg.py`

```python
import os
import glob
import cv2
import torch
import numpy as np
import imageio.v2 as imageio
import multiprocessing as mp
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

def run_nnunet_predict_and_overlay(input_dir: str, output_dir: str, model_dir: str, checkpoint: str = "checkpoint_final.pth"):
    for k in ['nnUNet_raw', 'nnUNet_preprocessed', 'nnUNet_results']:
        os.environ[k] = os.environ.get(k, f"./{k}")
        os.makedirs(os.environ[k], exist_ok=True)

    os.makedirs(output_dir, exist_ok=True)

    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=True,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        verbose=True,
        verbose_preprocessing=True,
    )
    predictor.initialize_from_trained_model_folder(
        model_dir,
        use_folds="all",
        checkpoint_name=checkpoint,
    )

    # —— 使用顺序处理模式，完全避免多进程 ——
    # predict_from_files_sequential 不使用任何多进程，避免与 FastAPI/uvicorn 冲突
    predictor.predict_from_files_sequential(
        input_dir,
        output_dir,
        save_probabilities=False,
    )

    print("🎯 Segmentation done.")
```

#### 2. `/media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc2/model-code/app.py` (核心修改)

在 `api_continue_after_l3` 函数中，使用子进程代替 FastAPI BackgroundTasks：

```python
        print(f"[API] 提交后台任务: {task_id}")
        print(f"[API] Input folder: {input_folder}")
        print(f"[API] Output folder: {output_folder}")

        # 使用独立子进程运行，完全隔离 CUDA/PyTorch 状态
        # 避免 C++ terminate 错误
        import subprocess
        import threading

        def run_in_subprocess():
            try:
                cmd = [
                    "python", "-c",
                    f"""
import os, sys
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
sys.path.insert(0, "{os.getcwd()}")
from all_new import continue_after_l3
result = continue_after_l3("{input_folder}", "{output_folder}")
print("SUBPROCESS_RESULT:", result)
"""
                ]

                task_status[task_id]["progress"] = 10
                task_status[task_id]["message"] = "正在处理..."

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=os.getcwd()
                )

                result_line = None
                for line in proc.stdout:
                    print(f"[子进程] {line.rstrip()}")
                    if line.startswith("SUBPROCESS_RESULT:"):
                        result_line = line

                proc.wait()

                if proc.returncode == 0:
                    task_status[task_id] = {
                        "status": "completed",
                        "progress": 100,
                        "message": "处理完成",
                        "result": result_line,
                        "started_at": task_status[task_id].get("started_at"),
                        "completed_at": time.time(),
                    }
                    print(f"[后台任务 {task_id}] 处理完成")
                else:
                    task_status[task_id] = {
                        "status": "failed",
                        "progress": 0,
                        "message": f"子进程退出码: {proc.returncode}",
                        "started_at": task_status[task_id].get("started_at"),
                        "failed_at": time.time(),
                    }
                    print(f"[后台任务 {task_id}] 处理失败: 退出码 {proc.returncode}")
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f"[后台任务 {task_id}] 异常: {e}\n{tb}")
                task_status[task_id] = {
                    "status": "failed",
                    "progress": 0,
                    "message": f"处理失败: {str(e)}",
                    "error": str(e),
                    "started_at": task_status[task_id].get("started_at"),
                    "failed_at": time.time(),
                }

        thread = threading.Thread(target=run_in_subprocess, daemon=True)
        thread.start()

        return {
            "status": "submitted",
            "task_id": task_id,
            "message": "任务已提交到后台处理，请轮询 /task_status/{task_id} 查看进度"
        }
```

## 验证结果

**成功修复！**

测试结果表明：
1. 第一次请求成功完成
2. 第二次、第三次连续请求都成功完成（无状态残留问题）
3. 服务器稳定运行，无崩溃现象

## 经验总结

### 1. 多进程与 FastAPI 事件循环的兼容性问题

FastAPI/Uvicorn 基于 asyncio 事件循环，对同步阻塞操作和多进程有严格要求：
- **避免在事件循环线程中运行阻塞操作**：如果必须运行，应使用 `run_in_threadpool` 或独立线程
- **避免使用 spawn 方式的 multiprocessing**：与 asyncio 事件循环高度冲突
- **子进程是最安全的隔离方式**：完全隔离状态，避免所有兼容性问题

### 2. nnUNet 部署注意事项

部署 nnUNet 到生产环境时：
- **使用顺序处理模式**：`predict_from_files_sequential` 避免多进程问题
- **限制线程数量**：设置 `torch.set_num_threads(1)` 和 `OMP_NUM_THREADS=1`
- **资源清理**：确保每次处理后释放 GPU 内存（`torch.cuda.empty_cache()`）
- **进程隔离**：对于长时间运行的服务，子进程隔离是最佳实践

### 3. 调试技巧

遇到类似问题时的调试步骤：
1. **捕获信号**：添加信号处理器定位关闭原因
2. **日志分析**：关注时间线和错误信息的关联
3. **状态隔离**：尝试独立进程/线程运行
4. **环境变量**：调整 OMP/MKL 线程数
5. **资源监控**：使用 `nvidia-smi` 监控 GPU 内存使用

## 运行命令

**启动服务器：**
```bash
cd /media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc2/model-code
export CRYPTOGRAPHY_OPENSSL_NO_LEGACY=1
python -m uvicorn app:app --host 0.0.0.0 --port 4200 --timeout-keep-alive 60
```

**监控日志：**
```bash
tail -f /media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc2/model-code/app.log
```

## 参考资料

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [nnUNetv2 Documentation](https://github.com/MIC-DKFZ/nnUNet/tree/master)
- [PyTorch Multiprocessing](https://pytorch.org/docs/stable/notes/multiprocessing.html)
- [Asyncio and Multiprocessing](https://docs.python.org/3/library/asyncio.html#asyncio-multiprocessing)