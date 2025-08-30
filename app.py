from fastapi import FastAPI, UploadFile, File, Form
import shutil, os
import zipfile
import zipfile
from all_new import main  # 重构 main 

app = FastAPI()
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