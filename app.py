from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import shutil, os, time, threading, hashlib, json
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Force immediate flush
import sys
for handler in logging.root.handlers:
    handler.flush = lambda: sys.stdout.flush() or sys.stderr.flush()

# ==================== 商业化系统集成 ====================
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置开关
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
ENABLE_QUOTA = os.getenv("ENABLE_QUOTA", "false").lower() == "true"

# 导入中间件（仅在需要时）
COMMERCIAL_AVAILABLE = False
auth_middleware = None
quota_middleware = None
init_quota_manager = None

if ENABLE_AUTH or ENABLE_QUOTA:
    try:
        import sys
        commercial_path = os.path.abspath('commercial')
        if commercial_path not in sys.path:
            sys.path.insert(0, commercial_path)
        
        if ENABLE_AUTH:
            from integrations.middleware.auth_middleware import auth_middleware
        
        if ENABLE_QUOTA:
            from integrations.middleware.quota_middleware import (
                quota_middleware,
                init_quota_manager
            )
        
        COMMERCIAL_AVAILABLE = True
        logger.info(f"🔐 认证中间件: {'✅ 启用' if ENABLE_AUTH else '❌ 关闭'}")
        logger.info(f"📊 配额中间件: {'✅ 启用' if ENABLE_QUOTA else '❌ 关闭'}")
    except ImportError as e:
        logger.error(f"⚠️ 商业化中间件导入失败: {e}")
        logger.warning("⚠️ 商业化功能已禁用")
        COMMERCIAL_AVAILABLE = False
        ENABLE_AUTH = False
        ENABLE_QUOTA = False
else:
    logger.info("ℹ️  商业化功能未启用（开发模式）")
# ==================== 商业化系统集成结束 ====================
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


logger.info("Creating FastAPI app...")
app = FastAPI()
logger.info("FastAPI app created")

# 全局任务状态字典 (后台计算)
task_status = {}

# 上传进度状态: {upload_id: {status, received, total, percent, message, folder, filename, started_at}}
upload_status = {}

# 每个病例(patient_date)的互斥锁，防止并发上传/处理覆盖
_patient_locks = {}
def _get_patient_lock(key: str):
    return _patient_locks.setdefault(key, threading.Lock())

# 每个任务的锁，防止重复提交
task_locks = {}
def _get_task_lock(task_id: str):
    return task_locks.setdefault(task_id, threading.Lock())

CHUNK_SIZE = 1024 * 512  # 512KB chunk

# Debug flag (enable extra instrumentation)
DEBUG_ENABLED = os.environ.get("IDOCTOR_DEBUG", "1") not in ("0", "false", "False")

def _patient_root(patient_name: str, study_date: str, user_id: str = None):
    """获取患者数据根目录（支持用户隔离）
    
    Args:
        patient_name: 患者名称
        study_date: 研究日期
        user_id: 用户ID（可选）
    
    Returns:
        数据目录路径
    """
    folder_name = f"{patient_name}_{study_date}"
    
    if user_id and ENABLE_AUTH:
        # 认证模式：数据按用户隔离
        user_data_root = os.path.join(DATA_ROOT, str(user_id))
        os.makedirs(user_data_root, exist_ok=True)
        return os.path.join(user_data_root, folder_name)
    else:
        # 开发模式：共享数据
        return os.path.join(DATA_ROOT, folder_name)

def _output_dir(patient_name: str, study_date: str, user_id: str = None):
    return os.path.join(_patient_root(patient_name, study_date, user_id), "output")

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
    "http://localhost:8080",  # Vue CLI 默认端口
    "http://127.0.0.1:8080",
    "http://localhost:3000",  # 常用开发端口
    "http://127.0.0.1:3000",
    "http://ai.bygpu.com:55304",  # 主前端（端口7500）
    "https://ai.bygpu.com:55304",
    "http://ai.bygpu.com:55305",  # commercial前端（端口3000）
    "https://ai.bygpu.com:55305",
    "http://ai.bygpu.com",
    "https://ai.bygpu.com",
    "http://ai.bygpu.com:55303",
    "https://ai.bygpu.com:55303",
]
logger.info("Adding CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware added")

# ==================== SAM2 分割服务集成 ====================
from sam2_client import get_sam2_client, init_sam2_client

SAM2_ENABLED = os.getenv("SAM2_ENABLED", "true").lower() == "true"
sam2_available = False

@app.on_event("startup")
async def startup_sam2():
    """Initialize SAM2 client on startup"""
    global sam2_available
    if SAM2_ENABLED:
        logger.info("🤖 Initializing SAM2 service...")
        sam2_available = await init_sam2_client()
        if sam2_available:
            logger.info("✅ SAM2 service initialized successfully")
        else:
            logger.warning("⚠️  SAM2 service unavailable - one-click segmentation disabled")
    else:
        logger.info("ℹ️  SAM2 service disabled")

# ==================== SAM2 分割服务集成结束 ====================

# ==================== 注册商业化中间件 ====================
logger.info(f"Registering commercial middleware... COMMERCIAL_AVAILABLE={COMMERCIAL_AVAILABLE}, ENABLE_AUTH={ENABLE_AUTH}, ENABLE_QUOTA={ENABLE_QUOTA}")
if COMMERCIAL_AVAILABLE and (ENABLE_AUTH or ENABLE_QUOTA):
    if ENABLE_QUOTA and init_quota_manager:
        # 初始化配额管理器
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            try:
                init_quota_manager(database_url)
                logger.info("✅ 配额管理器已初始化")
            except Exception as e:
                logger.error(f"⚠️ 配额管理器初始化失败: {e}", exc_info=True)
                ENABLE_QUOTA = False
        else:
            logger.warning("⚠️ 未配置 DATABASE_URL，配额功能将不可用")
            ENABLE_QUOTA = False

    # 注册中间件 (注意顺序：FastAPI 中间件是反向执行，所以后注册的先执行)
    # 我们希望：请求 → auth → quota → 路由
    # 所以注册顺序：先 quota，后 auth
    if ENABLE_QUOTA and quota_middleware:
        app.middleware("http")(quota_middleware)
        logger.info("✅ 配额中间件已注册")
    
    if ENABLE_AUTH and auth_middleware:
        app.middleware("http")(auth_middleware)
        logger.info("✅ 认证中间件已注册")
# ==================== 商业化中间件注册结束 ====================

# ==================== 注册管理路由 ====================
if COMMERCIAL_AVAILABLE and ENABLE_QUOTA:
    try:
        from integrations.admin_routes import router as admin_router
        app.include_router(admin_router)
        logger.info("✅ 管理API路由已注册")
    except Exception as e:
        logger.error(f"⚠️ 管理API路由注册失败: {e}")
# ==================== 管理路由注册结束 ====================

DATA_ROOT = "data"

############################## 健康检查和测试接口 ##############################
@app.get("/status")
def get_status(request: Request):
    """服务状态检查（用于测试认证）"""
    user_id = getattr(request.state, "user_id", None)
    user_email = getattr(request.state, "user_email", None)
    return {
        "status": "ok",
        "authenticated": user_id is not None,
        "user_id": user_id,
        "user_email": user_email,
        "enable_auth": ENABLE_AUTH,
        "enable_quota": ENABLE_QUOTA
    }

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
    # 获取用户ID
    user_id = getattr(request.state, "user_id", None)
    
    folder_name = f"{patient_name}_{study_date}"
    patient_root = _patient_root(patient_name, study_date, user_id)
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

        # 5. 同步存储使用量到数据库（如果启用了配额）
        if ENABLE_QUOTA and user_id:
            try:
                from integrations.storage_tracker import sync_storage_quota_to_db
                from integrations.quota_manager import QuotaManager

                # 异步同步存储配额
                import asyncio
                db_url = os.getenv("DATABASE_URL")
                if db_url:
                    qm = QuotaManager(db_url)
                    asyncio.create_task(sync_storage_quota_to_db(user_id, qm, DATA_ROOT))
                    logger.info(f"✅ Triggered storage quota sync for user {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to sync storage quota: {e}")
                # 存储同步失败不影响上传

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
    request: Request,
    patient_name: str, 
    study_date: str,
    background_tasks: BackgroundTasks
):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)
    
    task_id = f"main_{patient_name}_{study_date}"
    
    # 使用锁防止并发提交
    lock = _get_task_lock(task_id)
    if not lock.acquire(blocking=False):
        return {
            "status": "blocked",
            "task_id": task_id,
            "message": "任务正在处理中，请勿重复提交"
        }
    
    try:
        # 检查是否有正在运行的任务
        if task_id in task_status:
            status = task_status[task_id].get("status")
            # 如果是正在处理中的任务，返回现有状态
            if status == "processing":
                started = task_status[task_id].get("started_at", 0)
                elapsed = time.time() - started
                # 如果任务已经运行超过10分钟，认为是僵尸任务，允许重新提交
                if elapsed < 600:  # 10分钟
                    return {
                        "status": "processing",
                        "task_id": task_id,
                        "message": f"任务正在处理中(已运行 {int(elapsed)}秒)，请勿重复提交"
                    }
        
        # 初始化任务状态
        task_status[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "任务已提交",
            "started_at": time.time(),
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        folder_name = f"{patient_name}_{study_date}"
        patient_root = _patient_root(patient_name, study_date, user_id)
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
    finally:
        lock.release()

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

        # 彻底清理 full_overlay 目录
        full_overlay_dir = os.path.join(output_folder, "full_overlay")
        if os.path.isdir(full_overlay_dir):
            for f in os.listdir(full_overlay_dir):
                file_path = os.path.join(full_overlay_dir, f)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

        main(input_folder, output_folder)
        elapsed = time.time() - start
        if DEBUG_ENABLED:
            snap_after = _resource_snapshot()
            _append_log_line(output_folder, f"[TASK {task_id}] main() 完成 耗时={elapsed:.2f}s 资源after={snap_after}")
        task_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "全流程处理完成",
            "output_dir": output_folder,
            "started_at": task_status[task_id].get("started_at"),
            "completed_at": time.time(),
            "duration": elapsed
        }
    except Exception as e:
        tb = traceback.format_exc()
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] 异常: {e}\n{tb}")
        task_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "message": f"处理失败: {str(e)}",
            "error": str(e),
            "started_at": task_status[task_id].get("started_at"),
            "failed_at": time.time()
        }

# 返回所有文件夹的 病人-日期 列表
@app.get("/list_patients")
def list_patients(request: Request):
    """列出患者（支持用户隔离）"""
    user_id = getattr(request.state, "user_id", None)
    logger.info(f"list_patients called: user_id={user_id}, ENABLE_AUTH={ENABLE_AUTH}")

    if user_id and ENABLE_AUTH:
        # 认证模式：只列出该用户的患者
        user_data_root = os.path.join(DATA_ROOT, str(user_id))
        if not os.path.exists(user_data_root):
            return {"count": 0, "patients": []}
        search_root = user_data_root
    else:
        # 开发模式：列出所有患者
        search_root = DATA_ROOT
    
    patient_folders = [
        name for name in os.listdir(search_root)
        if os.path.isdir(os.path.join(search_root, name)) and not name.startswith('.')
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
def get_key_results(request: Request, patient_name: str, study_date: str):
    user_id = getattr(request.state, "user_id", None)
    
    patient_root = _patient_root(patient_name, study_date, user_id)
    full_overlay_folder = os.path.join(patient_root, "output", "full_overlay")
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
def get_image(request: Request, patient_name: str, study_date: str, filename: str):
    user_id = getattr(request.state, "user_id", None)

    patient_root = _patient_root(patient_name, study_date, user_id)
    img_path = os.path.join(patient_root, "output", "full_overlay", filename)
    if not os.path.exists(img_path):
        return {"error": "图片不存在"}

    # 创建 FileResponse 并添加 CORS 头
    response = FileResponse(img_path, media_type="image/png")

    # 添加 CORS 头以支持跨域访问
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response    

@app.post("/l3_detect/{patient_name}/{study_date}")
def api_l3_detect(request: Request, patient_name: str, study_date: str):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)
    
    patient_root = _patient_root(patient_name, study_date, user_id)
    input_folder = os.path.join(patient_root, "input")
    output_folder = os.path.join(patient_root, "output")
    os.makedirs(output_folder, exist_ok=True)
    result = l3_detect(input_folder, output_folder)
    return result

@app.post("/continue_after_l3/{patient_name}/{study_date}")
async def api_continue_after_l3(
    request: Request,
    patient_name: str, 
    study_date: str,
    background_tasks: BackgroundTasks
):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)
    
    task_id = f"cont_{patient_name}_{study_date}"
    
    # 使用锁防止并发提交
    lock = _get_task_lock(task_id)
    if not lock.acquire(blocking=False):
        return {
            "status": "blocked",
            "task_id": task_id,
            "message": "任务正在处理中，请勿重复提交"
        }
    
    try:
        # 检查是否有正在运行的任务
        if task_id in task_status:
            status = task_status[task_id].get("status")
            if status == "processing":
                started = task_status[task_id].get("started_at", 0)
                elapsed = time.time() - started
                if elapsed < 600:  # 10分钟
                    return {
                        "status": "processing",
                        "task_id": task_id,
                        "message": f"任务正在处理中(已运行 {int(elapsed)}秒)，请勿重复提交"
                    }
        
        # 初始化任务状态
        task_status[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "任务已提交",
            "started_at": time.time(),
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        patient_root = _patient_root(patient_name, study_date, user_id)
        input_folder = os.path.join(patient_root, "input")
        output_folder = os.path.join(patient_root, "output")
        
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
    finally:
        lock.release()

def _run_continue_after_l3(task_id: str, input_folder: str, output_folder: str):
    """后台任务：执行 continue_after_l3"""
    start = time.time()
    try:
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] ===== 开始 continue_after_l3() input={input_folder}")
            if os.path.isdir(output_folder):
                _append_log_line(output_folder, f"[TASK {task_id}] output初始: {os.listdir(output_folder)}")
        print(f"[后台任务 {task_id}] 开始处理...")
        task_status[task_id]["progress"] = 10
        task_status[task_id]["message"] = "正在读取 DICOM 和 L3 mask..."
        result = continue_after_l3(input_folder, output_folder)
        elapsed = time.time() - start
        print(f"[后台任务 {task_id}] 处理完成")
        if DEBUG_ENABLED:
            _append_log_line(output_folder, f"[TASK {task_id}] continue_after_l3() 完成 耗时={elapsed:.2f}s")
        task_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "处理完成",
            "result": result,
            "started_at": task_status[task_id].get("started_at"),
            "completed_at": time.time(),
            "duration": elapsed
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
            "error": str(e),
            "started_at": task_status[task_id].get("started_at"),
            "failed_at": time.time()
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
def get_debug_log(request: Request, patient_name: str, study_date: str, lines: int = 300):
    """获取指定病例 pipeline_debug.log 最后 N 行"""
    user_id = getattr(request.state, "user_id", None)
    output_folder = _output_dir(patient_name, study_date, user_id)
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
def get_output_image(request: Request, patient_name: str, study_date: str, folder: str, filename: str):
    # folder 例如 L3_overlay、L3_clean_mask、L3_png 等
    user_id = getattr(request.state, "user_id", None)
    patient_root = _patient_root(patient_name, study_date, user_id)
    file_path = os.path.join(patient_root, "output", folder, filename)
    if not os.path.exists(file_path):
        return {"error": "图片不存在"}

    # 创建 FileResponse 并添加 CORS 头
    response = FileResponse(file_path, media_type="image/png")

    # 添加 CORS 头以支持跨域访问
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response

@app.post("/generate_sagittal/{patient_name}/{study_date}")
def api_generate_sagittal(request: Request, patient_name: str, study_date: str, force: int = Query(0)):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)
    
    patient_root = _patient_root(patient_name, study_date, user_id)
    input_folder = os.path.join(patient_root, "input")
    output_folder = os.path.join(patient_root, "output")
    if not os.path.isdir(input_folder):
        return {"error": "请先上传 DICOM"}
    os.makedirs(output_folder, exist_ok=True)
    return generate_sagittal(input_folder, output_folder, force=bool(force))

@app.post("/upload_l3_mask/{patient}/{date}")
async def upload_l3_mask(request: Request, patient: str, date: str, file: UploadFile = File(...)):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)
    
    patient_root = _patient_root(patient, date, user_id)
    output_folder = os.path.join(patient_root, "output")
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
    request: Request,
    patient: str, date: str,
    psoas_mask: UploadFile = File(None),
    combo_mask: UploadFile = File(None)
):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)
    
    patient_root = _patient_root(patient, date, user_id)
    output_folder = os.path.join(patient_root, "output")
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
    
    # 清理 NaN/Inf 值
    import math
    def clean_floats(obj):
        if isinstance(obj, dict):
            return {k: clean_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_floats(v) for v in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
        return obj
    
    return clean_floats(result)

# ==================== SAM2 分割端点 ====================
@app.post("/api/segmentation/sam2")
async def sam2_segment(
    request: Request,
    file: UploadFile = File(...),
    image_type: str = Form("auto"),
    patient_id: str = Form(None),
    slice_index: str = Form(None),
    click_points: str = Form(None)
):
    """
    SAM2 分割端点 (支持交互式点击)

    Args:
        file: 图像文件 (PNG, JPEG)
        image_type: 图像类型 ("L3" 或 "middle" 或 "auto")
        patient_id: 患者ID (可选)
        slice_index: 切片索引 (可选)
        click_points: 点击坐标 JSON 字符串 (可选)
                     格式: '[{"x": 100, "y": 200, "label": 1}]'
                     label: 1=前景点, 0=背景点

    Returns:
        JSON response with mask_data (base64), confidence_score, processing_time_ms, cached, bounding_box
    """
    if not SAM2_ENABLED:
        raise HTTPException(status_code=503, detail="SAM2 service is disabled")

    sam2_client = get_sam2_client()

    # Check availability (async - will auto-refresh health check if needed)
    if not await sam2_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="SAM2 service is currently unavailable. Please try again later."
        )

    try:
        # 读取图像数据
        image_data = await file.read()

        # 验证图像格式
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Expected image/*, got {file.content_type}"
            )

        # 解析点击坐标
        parsed_click_points = None
        if click_points:
            try:
                parsed_click_points = json.loads(click_points)
                logger.info(f"Received {len(parsed_click_points)} click points for segmentation")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse click_points: {e}")

        # 调用 SAM2 分割
        mask_bytes, metadata = await sam2_client.segment_image(
            image_data=image_data,
            image_type=image_type,
            use_cache=True,
            click_points=parsed_click_points
        )

        if mask_bytes is None:
            error_msg = metadata.get("error", "Unknown error")
            raise HTTPException(status_code=500, detail=error_msg)

        # 编码 mask 为 base64
        import base64
        mask_base64 = base64.b64encode(mask_bytes).decode('utf-8')

        # 构建响应
        response = {
            "mask_data": mask_base64,
            "confidence_score": metadata.get("confidence_score", 0.0),
            "processing_time_ms": metadata.get("processing_time_ms", 0),
            "cached": metadata.get("cached", False),
            "bounding_box": metadata.get("bounding_box"),
            "image_type": image_type,
            "patient_id": patient_id,
            "slice_index": slice_index
        }

        logger.info(
            f"SAM2 segmentation successful: "
            f"type={image_type}, confidence={response['confidence_score']:.3f}, "
            f"cached={response['cached']}, time={response['processing_time_ms']}ms"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SAM2 segmentation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

@app.get("/api/segmentation/sam2/health")
async def sam2_health():
    """
    SAM2 服务健康检查端点

    Returns:
        JSON response with SAM2 service status
    """
    sam2_client = get_sam2_client()

    return {
        "enabled": SAM2_ENABLED,
        "available": await sam2_client.is_available(),
        "cache_stats": sam2_client.get_cache_stats()
    }

# ==================== SAM2 分割端点结束 ====================

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