from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import shutil, os, time, threading, hashlib, json
try:
    import psutil  # optional for memory diagnostics
except ImportError:  # graceful fallback
    psutil = None
import zipfile
import zipfile
import os
import traceback
from all_new import main 
from all_new import l3_detect, continue_after_l3, generate_sagittal, SAGITTAL_CLEAN
from fastapi.responses import FileResponse
from fastapi import FastAPI, UploadFile, File, Form, Query

from compute import compute_manual_middle_statistics


app = FastAPI()

# 全局任务状态字典 (后台计算)
task_status = {}

# 上传进度状态: {upload_id: {status, received, total, percent, message, folder, filename, started_at}}
upload_status = {}

# 每个病例(patient_date)的互斥锁，防止并发上传/处理覆盖
_patient_locks = {}
def _get_patient_lock(key: str):
    return _patient_locks.setdefault(key, threading.Lock())

CHUNK_SIZE = 1024 * 512  # 512KB chunk

# Debug flag (enable extra instrumentation)
DEBUG_ENABLED = os.environ.get("IDOCTOR_DEBUG", "1") not in ("0", "false", "False")

def _patient_root(patient_name: str, study_date: str):
    return os.path.join(DATA_ROOT, f"{patient_name}_{study_date}")

def _output_dir(patient_name: str, study_date: str):
    return os.path.join(_patient_root(patient_name, study_date), "output")

def _pipeline_log_path(output_folder: str):
    return os.path.join(output_folder, "pipeline_debug.log")

def _safe_mkdir(path: str):
    os.makedirs(path, exist_ok=True)

def _append_log_line(output_folder: str, line: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    full = f"[{ts}] {line}"
    print(full, flush=True)
    if not output_folder:
        return
    try:
        with open(_pipeline_log_path(output_folder), "a", encoding="utf-8") as f:
            f.write(full + "\n")
    except Exception:
        pass

def _hash_input_dir(input_dir: str):
    files = [f for f in os.listdir(input_dir) if f.lower().endswith((".dcm", ".dcm.pk"))]
    files.sort()
    h = hashlib.sha256()
    sizes = []
    for f in files:
        p = os.path.join(input_dir, f)
        try:
            st = os.stat(p)
            h.update(f.encode())
            h.update(str(st.st_size).encode())
            sizes.append(st.st_size)
        except Exception:
            continue
    return {
        "count": len(files),
        "hash": h.hexdigest(),
        "total_bytes": sum(sizes)
    }

def _resource_snapshot():
    snap = {}
    if psutil:
        p = psutil.Process()
        with p.oneshot():
            mem = p.memory_info()
            snap["rss_mb"] = round(mem.rss / 1024 / 1024, 2)
            snap["cpu_percent"] = p.cpu_percent(interval=None)
            snap["num_threads"] = p.num_threads()
            snap["open_files"] = len(p.open_files())
    return snap
# 允许的前端来源
origins = [
    "http://localhost:7500",
    "http://127.0.0.1:7500",
    "http://ai.bygpu.com:55304",
    "https://ai.bygpu.com:55304",
    "http://ai.bygpu.com",
    "https://ai.bygpu.com",
    "http://ai.bygpu.com:55303",   
    "https://ai.bygpu.com:55303", 
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_ROOT = "data"

############################## 上传相关接口 ##############################
@app.get("/upload_status/{upload_id}")
def get_upload_status(upload_id: str):
    """查询上传进度/状态"""
    return upload_status.get(upload_id, {"status": "not_found"})

@app.post("/upload_dicom_zip")
async def upload_dicom_zip(
    request: Request,
    patient_name: str = Form(...),
    study_date: str = Form(...),
    file: UploadFile = File(...),
    file_size: int = Form(None)
):
    """流式安全上传 + 进度 + 客户端断开清理 + 原子替换 input 目录。

    返回: {status, upload_id, folder, message}
    进度查询: GET /upload_status/{upload_id}
    状态说明:
      receiving -> unzip -> done / aborted / error
    """
    folder_name = f"{patient_name}_{study_date}"
    patient_root = os.path.join(DATA_ROOT, folder_name)
    os.makedirs(patient_root, exist_ok=True)

    lock = _get_patient_lock(folder_name)
    if not lock.acquire(blocking=False):
        return {"status": "blocked", "message": "该病例正在占用中, 稍后再试"}

    upload_id = f"{folder_name}_{int(time.time())}"
    upload_status[upload_id] = {
        "status": "receiving",
        "received": 0,
        "total": file_size,
        "percent": 0.0,
        "message": "正在接收",
        "folder": folder_name,
        "filename": file.filename,
        "started_at": time.time()
    }

    tmp_zip_path = os.path.join(patient_root, file.filename + ".part")
    tmp_input_dir = os.path.join(patient_root, f"input_uploading_{int(time.time())}")
    final_input_dir = os.path.join(patient_root, "input")
    backup_old = None

    try:
        # 1. 流式写入 zip .part
        with open(tmp_zip_path, "wb") as out_f:
            while True:
                if await request.is_disconnected():
                    raise RuntimeError("客户端已断开")
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                out_f.write(chunk)
                upload_status[upload_id]["received"] += len(chunk)
                if file_size:
                    upload_status[upload_id]["percent"] = round(upload_status[upload_id]["received"] / file_size * 100, 2)

        if file_size and upload_status[upload_id]["received"] != file_size:
            raise RuntimeError("接收字节与 file_size 不一致")

        upload_status[upload_id]["status"] = "unzip"
        upload_status[upload_id]["message"] = "解压中"

        # 2. 解压到临时目录
        os.makedirs(tmp_input_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
                for name in zf.namelist():
                    base = os.path.basename(name)
                    if not base:
                        continue
                    with zf.open(name) as src, open(os.path.join(tmp_input_dir, base), "wb") as dst:
                        shutil.copyfileobj(src, dst)
        except Exception as e:
            raise RuntimeError(f"解压失败: {e}")

        # 3. 原子替换 input 目录
        if os.path.isdir(final_input_dir):
            backup_old = final_input_dir + "_old"
            if os.path.isdir(backup_old):
                shutil.rmtree(backup_old, ignore_errors=True)
            os.replace(final_input_dir, backup_old)
        os.replace(tmp_input_dir, final_input_dir)
        if backup_old and os.path.isdir(backup_old):
            shutil.rmtree(backup_old, ignore_errors=True)

        # 4. 完成
        upload_status[upload_id]["status"] = "done"
        upload_status[upload_id]["message"] = "上传并解压成功"
        upload_status[upload_id]["percent"] = 100.0
        try:
            os.remove(tmp_zip_path)
        except Exception:
            pass
        return {"status": "ok", "upload_id": upload_id, "folder": folder_name, "message": "上传解压完成"}
    except Exception as e:
        upload_status[upload_id]["status"] = "aborted"
        upload_status[upload_id]["message"] = f"失败: {e}"
        # 清理临时
        try:
            if os.path.isfile(tmp_zip_path):
                os.remove(tmp_zip_path)
        except Exception:
            pass
        try:
            if os.path.isdir(tmp_input_dir):
                shutil.rmtree(tmp_input_dir, ignore_errors=True)
        except Exception:
            pass
        # 回滚旧 input
        if backup_old and not os.path.isdir(final_input_dir) and os.path.isdir(backup_old):
            os.replace(backup_old, final_input_dir)
        return {"status": "error", "upload_id": upload_id, "message": str(e)}
    finally:
        lock.release()

@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    patient_name: str, 
    study_date: str,
    background_tasks: BackgroundTasks
):
    task_id = f"main_{patient_name}_{study_date}"
    
    # 检查任务是否已在处理中
    if task_id in task_status and task_status[task_id]["status"] == "processing":
        return {
            "status": "processing",
            "task_id": task_id,
            "message": "任务正在处理中，请勿重复提交"
        }
    
    # 初始化任务状态
    task_status[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "任务已提交"
    }
    
    folder_name = f"{patient_name}_{study_date}"
    patient_root = os.path.join(DATA_ROOT, folder_name)
    input_folder = os.path.join(patient_root, "input")
    output_folder = os.path.join(patient_root, "output")
    os.makedirs(output_folder, exist_ok=True)

    print(f"[API] 提交全流程后台任务: {task_id}")
    
    # 提交后台任务
    background_tasks.add_task(_run_main_process, task_id, input_folder, output_folder)
    
    return {
        "status": "submitted",
        "task_id": task_id,
        "message": "全流程任务已提交到后台处理，请轮询 /task_status/{task_id} 查看进度"
    }

def _run_main_process(task_id: str, input_folder: str, output_folder: str):
    """后台任务：执行 main 全流程 (加调试日志)"""
    start = time.time()
    snap_before = _resource_snapshot() if DEBUG_ENABLED else {}
    if DEBUG_ENABLED:
        _append_log_line(output_folder, f"[TASK {task_id}] ===== 开始 main() input={input_folder}")
        inp_sig = _hash_input_dir(input_folder) if os.path.isdir(input_folder) else {"error": "input_missing"}
        _append_log_line(output_folder, f"[TASK {task_id}] 输入签名 {json.dumps(inp_sig, ensure_ascii=False)}")
        _append_log_line(output_folder, f"[TASK {task_id}] 资源快照(before) {snap_before}")
        # 列出 output 目录现有子目录(第二次运行时最关键)
        if os.path.isdir(output_folder):
            existing = os.listdir(output_folder)
            _append_log_line(output_folder, f"[TASK {task_id}] 现有output子项目: {existing}")
    try:
        task_status[task_id]["progress"] = 10
        task_status[task_id]["message"] = "正在处理..."
        main(input_folder, output_folder)
        elapsed = time.time() - start
        if DEBUG_ENABLED:
            snap_after = _resource_snapshot()
            _append_log_line(output_folder, f"[TASK {task_id}] main() 完成 耗时={elapsed:.2f}s 资源after={snap_after}")
        task_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "全流程处理完成",
            "output_dir": output_folder
        }
    except Exception as e:
        tb = traceback.format_exc()
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] 异常: {e}\n{tb}")
        task_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "message": f"处理失败: {str(e)}",
            "error": str(e)
        }

# 返回所有文件夹的 病人-日期 列表
@app.get("/list_patients")
def list_patients():
    patient_folders = [
        name for name in os.listdir(DATA_ROOT)
        if os.path.isdir(os.path.join(DATA_ROOT, name))
    ]
    # 转换为 病人-日期 格式
    patient_date_list = [
        name.replace("_", "-") for name in patient_folders
    ]
    return {
        "count": len(patient_date_list),
        "patients": patient_date_list
    }

# 根据病人名字和日期，返回 full_overlay 文件夹下的关键数据（两个 csv 文件和所有以 middle 结尾的图片）
@app.get("/get_key_results/{patient_name}/{study_date}")
def get_key_results(patient_name: str, study_date: str):
    folder_name = f"{patient_name}_{study_date}"
    full_overlay_folder = os.path.join(DATA_ROOT, folder_name, "output", "full_overlay")
    if not os.path.exists(full_overlay_folder):
        return {"error": "结果文件夹不存在"}

    files = os.listdir(full_overlay_folder)
    csv_files = [f for f in files if f.endswith(".csv")]
    middle_images = [f for f in files if f.endswith("middle.png")]

    # 读取 CSV 文件内容
    csv_contents = {}
    for f in csv_files:
        file_path = os.path.join(full_overlay_folder, f)
        with open(file_path, "r", encoding="utf-8") as file:
            csv_contents[f] = file.read()

    # 只返回 middle 图片的文件名
    return {
        "csv_files": csv_contents,      # {文件名: 内容}
        "middle_images": middle_images  # [文件名, ...]
    }

# 直接传输图片文件
@app.get("/get_image/{patient_name}/{study_date}/{filename}")
def get_image(patient_name: str, study_date: str, filename: str):
    folder_name = f"{patient_name}_{study_date}"
    img_path = os.path.join(DATA_ROOT, folder_name, "output", "full_overlay", filename)
    if not os.path.exists(img_path):
        return {"error": "图片不存在"}
    return FileResponse(img_path, media_type="image/png")    

@app.post("/l3_detect/{patient_name}/{study_date}")
def api_l3_detect(patient_name: str, study_date: str):
    folder = f"{patient_name}_{study_date}"
    input_folder = os.path.join(DATA_ROOT, folder, "input")
    output_folder = os.path.join(DATA_ROOT, folder, "output")
    os.makedirs(output_folder, exist_ok=True)
    result = l3_detect(input_folder, output_folder)
    return result

@app.post("/continue_after_l3/{patient_name}/{study_date}")
async def api_continue_after_l3(
    patient_name: str, 
    study_date: str,
    background_tasks: BackgroundTasks
):
    task_id = f"{patient_name}_{study_date}"
    
    # 检查任务是否已在处理中
    if task_id in task_status and task_status[task_id]["status"] == "processing":
        return {
            "status": "processing",
            "task_id": task_id,
            "message": "任务正在处理中，请勿重复提交"
        }
    
    # 初始化任务状态
    task_status[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "任务已提交"
    }
    
    folder = f"{patient_name}_{study_date}"
    input_folder = os.path.join(DATA_ROOT, folder, "input")
    output_folder = os.path.join(DATA_ROOT, folder, "output")
    
    print(f"[API] 提交后台任务: {task_id}")
    print(f"[API] Input folder: {input_folder}")
    print(f"[API] Output folder: {output_folder}")
    
    # 提交后台任务
    background_tasks.add_task(_run_continue_after_l3, task_id, input_folder, output_folder)
    
    return {
        "status": "submitted",
        "task_id": task_id,
        "message": "任务已提交到后台处理，请轮询 /task_status/{task_id} 查看进度"
    }

def _run_continue_after_l3(task_id: str, input_folder: str, output_folder: str):
    """后台任务：执行 continue_after_l3"""
    try:
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] ===== 开始 continue_after_l3() input={input_folder}")
            if os.path.isdir(output_folder):
                _append_log_line(output_folder, f"[TASK {task_id}] output初始: {os.listdir(output_folder)}")
        print(f"[后台任务 {task_id}] 开始处理...")
        task_status[task_id]["progress"] = 10
        task_status[task_id]["message"] = "正在读取 DICOM 和 L3 mask..."
        result = continue_after_l3(input_folder, output_folder)
        print(f"[后台任务 {task_id}] 处理完成")
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] continue_after_l3() 完成")
        task_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "处理完成",
            "result": result
        }
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[后台任务 {task_id}] 处理失败: {e}")
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] continue_after_l3 异常: {e}\n{tb}")
        task_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "message": f"处理失败: {str(e)}",
            "error": str(e)
        }

@app.get("/task_status/{task_id}")
def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in task_status:
        return {
            "status": "not_found",
            "message": "任务不存在"
        }
    return task_status[task_id]

@app.get("/list_tasks")
def list_tasks():
    """列出所有任务及其状态"""
    return {
        "tasks": task_status,
        "count": len(task_status)
    }

@app.get("/debug_log/{patient_name}/{study_date}")
def get_debug_log(patient_name: str, study_date: str, lines: int = 300):
    """获取指定病例 pipeline_debug.log 最后 N 行"""
    output_folder = _output_dir(patient_name, study_date)
    log_path = _pipeline_log_path(output_folder)
    if not os.path.isfile(log_path):
        raise HTTPException(status_code=404, detail="log 不存在")
    if lines <= 0:
        lines = 200
    # 读取尾部
    data = []
    with open(log_path, "r", encoding="utf-8") as f:
        # 简易尾读
        from collections import deque
        dq = deque(f, maxlen=lines)
        data = list(dq)
    return {"patient": patient_name, "study_date": study_date, "lines": len(data), "content": data}

@app.get("/get_output_image/{patient_name}/{study_date}/{folder}/{filename}")
def get_output_image(patient_name: str, study_date: str, folder: str, filename: str):
    # folder 例如 L3_overlay、L3_clean_mask、L3_png 等
    file_path = os.path.join(
        DATA_ROOT, f"{patient_name}_{study_date}", "output", folder, filename
    )
    if not os.path.exists(file_path):
        return {"error": "图片不存在"}
    return FileResponse(file_path, media_type="image/png")

@app.post("/generate_sagittal/{patient_name}/{study_date}")
def api_generate_sagittal(patient_name: str, study_date: str, force: int = Query(0)):
    folder = f"{patient_name}_{study_date}"
    input_folder = os.path.join(DATA_ROOT, folder, "input")
    output_folder = os.path.join(DATA_ROOT, folder, "output")
    if not os.path.isdir(input_folder):
        return {"error": "请先上传 DICOM"}
    os.makedirs(output_folder, exist_ok=True)
    return generate_sagittal(input_folder, output_folder, force=bool(force))

@app.post("/upload_l3_mask/{patient}/{date}")
async def upload_l3_mask(patient: str, date: str, file: UploadFile = File(...)):
    folder = f"{patient}_{date}"
    output_folder = os.path.join("data", folder, "output")
    png_dir = os.path.join(output_folder, "L3_png")
    if not os.path.exists(os.path.join(png_dir, SAGITTAL_CLEAN)):
        return {"error": "请先调用 /generate_sagittal"}

    mask_dir = os.path.join(output_folder, "L3_mask")
    clean_dir = os.path.join(output_folder, "L3_clean_mask")
    overlay_dir = os.path.join(output_folder, "L3_overlay")
    for d in [mask_dir, clean_dir, overlay_dir]:
        os.makedirs(d, exist_ok=True)

    save_path = os.path.join(mask_dir, SAGITTAL_CLEAN)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    from sagit_save import clean_mask_folder, overlay_and_save
    clean_mask_folder(mask_dir, clean_dir)
    overlay_and_save(png_dir, clean_dir, overlay_dir)
    return {"status": "ok", "message": "手动 L3 mask 已覆盖", "overlay": f"L3_overlay/{SAGITTAL_CLEAN}"}

@app.post("/upload_middle_manual_mask/{patient}/{date}")
async def upload_middle_manual_mask(
    patient: str, date: str,
    psoas_mask: UploadFile = File(None),
    combo_mask: UploadFile = File(None)
):
    folder = f"{patient}_{date}"
    output_folder = os.path.join("data", folder, "output")
    full_overlay_dir = os.path.join(output_folder, "full_overlay")
    manual_mask_dir = os.path.join(output_folder, "manual_middle_mask")
    axisal_dir = os.path.join(output_folder, "Axisal")

    # 确保 manual_middle_mask 目录存在
    os.makedirs(manual_mask_dir, exist_ok=True)

    # 清空 old 文件（只删 middle 相关图片和 mask，不删 csv）
    safe_clear_folder(full_overlay_dir, ["_middle.png"])
    safe_clear_folder(manual_mask_dir, ["_psoas.png", "_combo.png"])

    # 读取 full_overlay/hu_statistics_middle_only.csv，定位 filename
    csv_path = os.path.join(full_overlay_dir, "hu_statistics_middle_only.csv")
    import pandas as pd
    if not os.path.isfile(csv_path):
        return {"error": "缺少 hu_statistics_middle_only.csv"}
    df = pd.read_csv(csv_path)
    if "filename" not in df.columns or df.empty:
        return {"error": "CSV 文件无有效 filename"}
    middle_name = df.iloc[0]["filename"]  # 例如 slice_105_middle.png

    base_name = middle_name.replace("_middle.png", ".png")
    axisal_path = os.path.join(axisal_dir, base_name)
    if not os.path.isfile(axisal_path):
        return {"error": f"未找到原图 {base_name}"}

    # 保存 psoas mask
    psoas_mask_path = os.path.join(manual_mask_dir, f"{base_name}_psoas.png")
    if psoas_mask is not None:
        with open(psoas_mask_path, "wb") as f:
            f.write(await psoas_mask.read())
    else:
        psoas_mask_path = None

    # 保存 combo mask
    combo_mask_path = os.path.join(manual_mask_dir, f"{base_name}_combo.png")
    if combo_mask is not None:
        with open(combo_mask_path, "wb") as f:
            f.write(await combo_mask.read())
    else:
        combo_mask_path = None

    # 统计并生成 overlay
    result = compute_manual_middle_statistics(axisal_path, psoas_mask_path, combo_mask_path, full_overlay_dir, base_name)
    return result

def safe_clear_folder(folder, patterns):
    if not os.path.isdir(folder):
        return
    for fname in os.listdir(folder):
        for pat in patterns:
            if fname.endswith(pat):
                try:
                    os.remove(os.path.join(folder, fname))
                except Exception:
                    pass