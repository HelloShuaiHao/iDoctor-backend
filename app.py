from fastapi import FastAPI, UploadFile, File, Form
import shutil, os
import zipfile

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
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(input_folder)
    return {"folder": folder_name, "message": "上传并解压成功"}

