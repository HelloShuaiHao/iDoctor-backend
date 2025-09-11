import SimpleITK as sitk
import cv2
import os
import numpy as np
import torch
import multiprocessing as mp
from sagit_save import resize_and_save_sagittal_as_dicom, dicom_to_balanced_png, overlay_and_save, clean_mask_folder
from extract_slice import load_mask, extract_axial_slices_from_sagittal_mask, reversedNumber, convert_selected_slices
from seg import run_nnunet_predict_and_overlay
from compute import process_all

SAGITTAL_BASE = "sagittal_midResize"
SAGITTAL_INPUT = SAGITTAL_BASE + "_0000.png"   # nnUNet 输入文件
SAGITTAL_CLEAN = SAGITTAL_BASE + ".png"        # 前端&手动标注&最终mask统一文件


def main(input_folder, output_folder):
    # 输出目录
    # dicom_folder = "1504425"
    # # L3相关
    # L3_png_folder = f"L3_png_{dicom_folder}"
    # L3_mask_folder = f"L3_mask_{dicom_folder}"
    # L3_cleaned_mask_folder = f"L3_clean_mask_{dicom_folder}"
    # L3_overlay_folder = f"L3_overlay_{dicom_folder}"  # 需要展示在前端
    # # 横切图
    # slice_folder = f"Axisal_{dicom_folder}"
    # # 肌肉分割
    # full_mask_folder = f"full_mask_{dicom_folder}"
    # clean_full_mask_folder = f"clean_{dicom_folder}"
    # full_overlay_folder = f"full_overlay_{dicom_folder}" # 展示在前端
    # major_mask_folder = f"major_mask_{dicom_folder}"
    # major_overlay_folder = f"major_overlay_{dicom_folder}" # 展示在前端

    dicom_folder = input_folder
    # 所有输出目录都在 output_folder 下
    L3_png_folder = os.path.join(output_folder, "L3_png")
    L3_mask_folder = os.path.join(output_folder, "L3_mask")
    L3_cleaned_mask_folder = os.path.join(output_folder, "L3_clean_mask")
    L3_overlay_folder = os.path.join(output_folder, "L3_overlay")
    slice_folder = os.path.join(output_folder, "Axisal")
    full_mask_folder = os.path.join(output_folder, "full_mask")
    clean_full_mask_folder = os.path.join(output_folder, "clean")
    full_overlay_folder = os.path.join(output_folder, "full_overlay")
    major_mask_folder = os.path.join(output_folder, "major_mask")
    major_overlay_folder = os.path.join(output_folder, "major_overlay")


    # 模型路径
    L3_model_dir = "nnUNet_results/Dataset003_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    L3_checkpoint = "checkpoint_final.pth"
    full_model_dir="nnUNet_results/Dataset001_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    full_checkpoint="checkpoint_final.pth"

    major_model_dir="nnUNet_results/Dataset002_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    major_checkpoint="checkpoint_final.pth"

    # 1. 找中间视角的侧视图
    # Load 3D volume
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()

    volume = sitk.GetArrayFromImage(image)  # [Z, Y, X]
    spacing = image.GetSpacing()

    spacing_z = spacing[2]  # height direction
    spacing_y = spacing[1]  # width direction
    scale_ratio = spacing_z / spacing_y

    # Extract middle sagittal slice
    x_mid = volume.shape[2] // 2
    sagittal_slice = volume[:, :, x_mid]
    orig_height, orig_width = sagittal_slice.shape

    # DICOM:Save with resized height and updated metadata
    dcm_path = resize_and_save_sagittal_as_dicom(sagittal_slice, spacing, dicom_names[len(dicom_names)//2])

    # Convert to png
    # png_path = dicom_to_balanced_png(dcm_path, f"output7_{dicom_folder}.png", scale_ratio)
    png_path = dicom_to_balanced_png(dcm_path, L3_png_folder, scale_ratio)

    # 2. 推理L3脊柱
    # return mask和overlay的地址
    # mask_path, overlay_path = process_image(image_path, L3_weights_path, L3_output_folder)
    run_nnunet_predict_and_overlay(L3_png_folder, L3_mask_folder, L3_model_dir, L3_checkpoint)
    
    clean_mask_folder(L3_mask_folder, L3_cleaned_mask_folder)
    # overlay!!
    overlay_and_save(L3_png_folder, L3_cleaned_mask_folder, L3_overlay_folder)

    # Generate or load mask
    image_path = os.path.join(L3_cleaned_mask_folder, "sagittal_midResize.png")
    mask = load_mask(image_path)
    restored_mask = cv2.resize(mask, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)

    # 3. 找对应的横切图
    # Extract corresponding axial slices
    axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, restored_mask, x_mid, save_images=False)
    selectedNumbers = reversedNumber(volume.shape[0], axial_slices_numbers)

    # convert_selected_slices(dicom_folder, slice_folder, seleactedNumbers)
    convert_selected_slices(
        dicom_folder=dicom_folder,
        output_folder=slice_folder,
        selected_slices=selectedNumbers
    )

    # 4. 腰大肌的识别
    run_nnunet_predict_and_overlay(slice_folder, major_mask_folder, major_model_dir, major_checkpoint)
    # 5. 全肌肉的识别
    run_nnunet_predict_and_overlay(slice_folder, full_mask_folder, full_model_dir, full_checkpoint)

    for filename in os.listdir(slice_folder):
        if filename.endswith("_0000.png"):
            name_wo_ext = filename[:-9]
            old_path = os.path.join(slice_folder, filename)
            new_path = os.path.join(slice_folder, name_wo_ext + ".png")
            os.rename(old_path, new_path)
            print(f"Renamed: {filename} → {name_wo_ext}.png")

    # 6 全肌肉 + 腰大肌一起计算
    process_all(
        psoas_mask_dir=major_mask_folder,
        full_mask_dir=full_mask_folder,
        slice_dir=slice_folder,
        dicom_dir=dicom_folder,
        overlay_psoas_dir=major_overlay_folder,
        overlay_combo_dir=full_overlay_folder,
        clean_full_mask_dir=clean_full_mask_folder,
        pattern="*.png",
        area_thresh=1000,
        area_ratio_thresh=0.05,
        morph_ksize=3,
        morph_iters=1,
        overlay_alpha=0.5
    )

def l3_detect(input_folder, output_folder):
    L3_png_folder = os.path.join(output_folder, "L3_png")
    L3_mask_folder = os.path.join(output_folder, "L3_mask")
    L3_cleaned_mask_folder = os.path.join(output_folder, "L3_clean_mask")
    L3_overlay_folder = os.path.join(output_folder, "L3_overlay")
    for d in [L3_png_folder, L3_mask_folder, L3_cleaned_mask_folder, L3_overlay_folder]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(os.path.join(L3_png_folder, SAGITTAL_CLEAN)):
        generate_sagittal(input_folder, output_folder, force=False)

    # 自动分割
    L3_model_dir = "nnUNet_results/Dataset003_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    L3_checkpoint = "checkpoint_final.pth"
    run_nnunet_predict_and_overlay(L3_png_folder, L3_mask_folder, L3_model_dir, L3_checkpoint)

    # 标准化：如果输出是 *_0000.png → 改成 sagittal_midResize.png
    for f in os.listdir(L3_mask_folder):
        if f.startswith(SAGITTAL_BASE) and f.endswith("_0000.png"):
            os.replace(os.path.join(L3_mask_folder, f),
                       os.path.join(L3_mask_folder, SAGITTAL_CLEAN))

    clean_mask_folder(L3_mask_folder, L3_cleaned_mask_folder)
    overlay_and_save(L3_png_folder, L3_cleaned_mask_folder, L3_overlay_folder)

    return {
        "sagittal_png": f"L3_png/{SAGITTAL_CLEAN}",
        "l3_mask": f"L3_clean_mask/{SAGITTAL_CLEAN}",
        "l3_overlay": f"L3_overlay/{SAGITTAL_CLEAN}",
        "auto": True
    }

def continue_after_l3(input_folder, output_folder):
    # 只做横断面提取和后续分割
    L3_cleaned_mask_folder = os.path.join(output_folder, "L3_clean_mask")
    mask_path = os.path.join(L3_cleaned_mask_folder, SAGITTAL_CLEAN)
    if not os.path.exists(mask_path):
        return {"error": "缺少 L3_clean_mask/sagittal_midResize.png，请先自动或手动上传"}
    
    slice_folder = os.path.join(output_folder, "Axisal")
    full_mask_folder = os.path.join(output_folder, "full_mask")
    clean_full_mask_folder = os.path.join(output_folder, "clean")
    full_overlay_folder = os.path.join(output_folder, "full_overlay")
    major_mask_folder = os.path.join(output_folder, "major_mask")
    major_overlay_folder = os.path.join(output_folder, "major_overlay")

    # 读取 DICOM
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(input_folder)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    volume = sitk.GetArrayFromImage(image)
    orig_height, orig_width = volume.shape[1], volume.shape[2]
    x_mid = volume.shape[2] // 2

    # 恢复 mask
    image_path = os.path.join(L3_cleaned_mask_folder, "sagittal_midResize.png")
    mask = load_mask(image_path)
    restored_mask = cv2.resize(mask, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)

    # 横断面提取
    axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, restored_mask, x_mid, save_images=False)
    selectedNumbers = reversedNumber(volume.shape[0], axial_slices_numbers)
    convert_selected_slices(
        dicom_folder=input_folder,
        output_folder=slice_folder,
        selected_slices=selectedNumbers
    )

    # 肌肉分割
    full_model_dir="nnUNet_results/Dataset001_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    full_checkpoint="checkpoint_final.pth"
    major_model_dir="nnUNet_results/Dataset002_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    major_checkpoint="checkpoint_final.pth"
    run_nnunet_predict_and_overlay(slice_folder, major_mask_folder, major_model_dir, major_checkpoint)
    run_nnunet_predict_and_overlay(slice_folder, full_mask_folder, full_model_dir, full_checkpoint)

    for filename in os.listdir(slice_folder):
        if filename.endswith("_0000.png"):
            name_wo_ext = filename[:-9]
            old_path = os.path.join(slice_folder, filename)
            new_path = os.path.join(slice_folder, name_wo_ext + ".png")
            os.rename(old_path, new_path)

    process_all(
        psoas_mask_dir=major_mask_folder,
        full_mask_dir=full_mask_folder,
        slice_dir=slice_folder,
        dicom_dir=input_folder,
        overlay_psoas_dir=major_overlay_folder,
        overlay_combo_dir=full_overlay_folder,
        clean_full_mask_dir=clean_full_mask_folder,
        pattern="*.png",
        area_thresh=1000,
        area_ratio_thresh=0.05,
        morph_ksize=3,
        morph_iters=1,
        overlay_alpha=0.5
    )
    return {"status": "ok", "message": "后续流程已完成"}

def generate_sagittal(input_folder, output_folder, force=False):
    L3_png_folder = os.path.join(output_folder, "L3_png")
    os.makedirs(L3_png_folder, exist_ok=True)
    clean_target = os.path.join(L3_png_folder, SAGITTAL_CLEAN)
    if (not force) and os.path.exists(clean_target):
        return {"sagittal_png": f"L3_png/{SAGITTAL_CLEAN}", "regenerated": False}

    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(input_folder)
    if len(dicom_names) == 0:
        raise RuntimeError("未找到 DICOM")
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    vol = sitk.GetArrayFromImage(image)
    spacing = image.GetSpacing()
    x_mid = vol.shape[2] // 2
    sag = vol[:, :, x_mid]

    dcm_path = resize_and_save_sagittal_as_dicom(
        sag, spacing, dicom_names[len(dicom_names)//2]
    )
    dicom_to_balanced_png(dcm_path, L3_png_folder, scale_ratio=1.0, base_name=SAGITTAL_BASE)
    return {"sagittal_png": f"L3_png/{SAGITTAL_CLEAN}", "regenerated": True}

if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    main()