from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

import shutil, os
import zipfile
import zipfile
import os
from all_new import main 
from all_new import l3_detect, continue_after_l3, generate_sagittal, SAGITTAL_CLEAN
from fastapi.responses import FileResponse
from fastapi import FastAPI, UploadFile, File, Form, Query

from compute import compute_manual_middle_statistics


app = FastAPI()
# 允许的前端来源
origins = [
    "http://localhost:7500",
    "http://127.0.0.1:7500",
    "http://ai.bygpu.com:55304",
    "https://ai.bygpu.com:55304",
    "http://ai.bygpu.com",
    "https://ai.bygpu.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_ROOT = "data"

# 测试命令 curl -F "patient_name=张三" -F "study_date=20230830" -F "file=@test.zip" http://localhost:8000/upload_dicom_zip
@app.post("/upload_dicom_zip")
async def upload_dicom_zip(
    patient_name: str = Form(...),
    study_date: str = Form(...),
    file: UploadFile = File(...)
):
    folder_name = f"{patient_name}_{study_date}"
    patient_root = os.path.join(DATA_ROOT, folder_name)
    input_folder = os.path.join(patient_root, "input")
    os.makedirs(input_folder, exist_ok=True)
    zip_path = os.path.join(patient_root, file.filename)
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # 解压时将所有文件直接放到 input_folder
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            filename = os.path.basename(member)
            if not filename:
                continue  # 跳过文件夹
            source = zip_ref.open(member)
            target = open(os.path.join(input_folder, filename), "wb")
            with source, target:
                shutil.copyfileobj(source, target)
    os.remove(zip_path)  # 解压后删除 zip 文件                
    return {"folder": folder_name, "message": "上传并解压成功"}

@app.post("/process/{patient_name}/{study_date}")
def process_case(patient_name: str, study_date: str):
    folder_name = f"{patient_name}_{study_date}"
    patient_root = os.path.join(DATA_ROOT, folder_name)
    input_folder = os.path.join(patient_root, "input")
    output_folder = os.path.join(patient_root, "output")
    os.makedirs(output_folder, exist_ok=True)

    main(input_folder, output_folder)

    return {
        "status": "success",
        "message": "处理完成",
        "output_dir": output_folder
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
def api_continue_after_l3(patient_name: str, study_date: str):
    folder = f"{patient_name}_{study_date}"
    input_folder = os.path.join(DATA_ROOT, folder, "input")
    output_folder = os.path.join(DATA_ROOT, folder, "output")
    result = continue_after_l3(input_folder, output_folder)
    return result

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