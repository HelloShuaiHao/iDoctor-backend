import SimpleITK as sitk
import cv2
import os
import numpy as np
import torch
import multiprocessing as mp
from datetime import datetime
from pipeline_logging import write_log, log_section
from sagit_save import resize_and_save_sagittal_as_dicom, dicom_to_balanced_png, overlay_and_save, clean_mask_folder
from verseg import process_spine_and_vertebrae
from extract_slice import load_mask, extract_axial_slices_from_sagittal_mask, reversedNumber, convert_selected_slices

from extract_slice import load_mask, extract_axial_slices_from_sagittal_mask,convert_selected_slices
from extract_slice import convert_selected_slices_by_z_index

from seg import run_nnunet_predict_and_overlay
from compute import process_all

SAGITTAL_BASE = "sagittal_midResize"
SAGITTAL_INPUT = SAGITTAL_BASE + "_0000.png"   # nnUNet 输入文件
SAGITTAL_CLEAN = SAGITTAL_BASE + ".png"        # 前端&手动标注&最终mask统一文件


def main(input_folder, output_folder):
    log_section(output_folder, f"MAIN START input={input_folder}")
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
    # L3_mask_folder = os.path.join(output_folder, "L3_mask")
    # L3_cleaned_mask_folder = os.path.join(output_folder, "L3_clean_mask")
    # L3_overlay_folder = os.path.join(output_folder, "L3_overlay")
    ver_folder = os.path.join(output_folder, "verseg")
    slice_folder = os.path.join(output_folder, "Axisal")
    # 清理 Axisal 目录下所有 png 文件
    safe_clear_folder(slice_folder, [".png"])
    full_mask_folder = os.path.join(output_folder, "full_mask")
    clean_full_mask_folder = os.path.join(output_folder, "clean")
    full_overlay_folder = os.path.join(output_folder, "full_overlay")
    major_mask_folder = os.path.join(output_folder, "major_mask")
    major_overlay_folder = os.path.join(output_folder, "major_overlay")


    # 模型路径
    whole_weights = "outputwhole/model_final.pth"
    vertebra_weights = "outputnew/model_final.pth"
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
    write_log(output_folder, f"DICOM loaded count={len(dicom_names)} volume_shape={volume.shape} spacing={spacing}")

    spacing_z = spacing[2]  # height direction
    spacing_y = spacing[1]  # width direction
    scale_ratio = spacing_z / spacing_y

    # Extract middle sagittal slice
    x_mid = volume.shape[2] // 2
    sagittal_slice = volume[:, :, x_mid]
    orig_height, orig_width = sagittal_slice.shape

    # DICOM:Save with resized height and updated metadata
    dcm_path = resize_and_save_sagittal_as_dicom(sagittal_slice, spacing, dicom_names[len(dicom_names)//2])
    write_log(output_folder, f"Sagittal DICOM saved path={dcm_path} slice_shape={sagittal_slice.shape}")

    # Convert to png
    # png_path = dicom_to_balanced_png(dcm_path, f"output7_{dicom_folder}.png", scale_ratio)
    png_inputs = dicom_to_balanced_png(dcm_path, L3_png_folder, scale_ratio)
    write_log(output_folder, f"Sagittal PNG generated dir={L3_png_folder} files={os.listdir(L3_png_folder)}")

    # 2. 推理L3脊柱
    # return mask和overlay的地址
    # mask_path, overlay_path = process_image(image_path, L3_weights_path, L3_output_folder)
    clean_nnunet_input_folder(slice_folder)


    """
    2025/10/06
    更改脊椎推理模型，可以推理出L1~L5，目前只取L3
    之后根据L3的mask来提取横切图
    输出： L3的mask_path, 整个脊椎的overlay_path，分割每个锥体的overlay_path
    """
    img_path = os.path.join(L3_png_folder, SAGITTAL_INPUT)
    write_log(output_folder, "Begin vertebra detection")
    results = process_spine_and_vertebrae(img_path, whole_weights, vertebra_weights, ver_folder)
    write_log(output_folder, f"Vertebra detection done keys={list(results.keys()) if results else None}")
    L3_mask_path = results["L3_mask"]
    write_log(output_folder, f"L3_mask_path={L3_mask_path} exists={os.path.exists(L3_mask_path)}")
    mask = load_mask(L3_mask_path)
    restored_mask = cv2.resize(mask, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)
    write_log(output_folder, f"L3 mask loaded shape={mask.shape} resized_shape={restored_mask.shape} foreground_pixels={int(mask.sum())}")

    # 3. 找对应的横切图
    # Extract corresponding axial slices
    axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, restored_mask, x_mid, save_images=False)
    if axial_slices_numbers:
        preview = axial_slices_numbers[:2] + axial_slices_numbers[-2:]
    else:
        preview = []
    write_log(output_folder, f"Axial indices count={len(axial_slices_numbers)} preview={preview}")
    convert_selected_slices_by_z_index(
        dicom_folder=dicom_folder,
        output_folder=slice_folder,
        selected_z_indices=axial_slices_numbers
    )
    
    selectedNumbers = reversedNumber(volume.shape[0], axial_slices_numbers)

    # convert_selected_slices(dicom_folder, slice_folder, seleactedNumbers)
    convert_selected_slices(
        dicom_folder=dicom_folder,
        output_folder=slice_folder,
        selected_slices=selectedNumbers
    )

    # 4. 腰大肌的识别
    write_log(output_folder, f"Run psoas nnUNet input_dir={slice_folder} output={major_mask_folder}")
    run_nnunet_predict_and_overlay(slice_folder, major_mask_folder, major_model_dir, major_checkpoint)
    write_log(output_folder, f"Psoas nnUNet done outputs={len(os.listdir(major_mask_folder))}")
    # 5. 全肌肉的识别
    write_log(output_folder, f"Run full nnUNet input_dir={slice_folder} output={full_mask_folder}")
    run_nnunet_predict_and_overlay(slice_folder, full_mask_folder, full_model_dir, full_checkpoint)
    write_log(output_folder, f"Full nnUNet done outputs={len(os.listdir(full_mask_folder))}")

    before_rename = [f for f in os.listdir(slice_folder) if f.endswith('_0000.png')]
    write_log(output_folder, f"Rename phase start count_0000={len(before_rename)}")
    for filename in os.listdir(slice_folder):
        if filename.endswith("_0000.png"):
            name_wo_ext = filename[:-9]
            old_path = os.path.join(slice_folder, filename)
            new_path = os.path.join(slice_folder, name_wo_ext + ".png")
            os.rename(old_path, new_path)
    after_rename = [f for f in os.listdir(slice_folder) if f.endswith('.png')]
    write_log(output_folder, f"Rename phase done total_png={len(after_rename)}")

    # 6 全肌肉 + 腰大肌一起计算
    write_log(output_folder, "Begin process_all metrics computation")
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
    write_log(output_folder, "process_all done")
    log_section(output_folder, "MAIN END")

def l3_detect(input_folder, output_folder):
    write_log(output_folder, f"L3_DETECT START input={input_folder}")
    L3_png_folder = os.path.join(output_folder, "L3_png")
    ver_folder = os.path.join(output_folder, "verseg")
    L3_mask_folder = os.path.join(output_folder, "L3_mask")
    L3_clean_mask_folder = os.path.join(output_folder, "L3_clean_mask")
    L3_overlay_folder = os.path.join(output_folder, "L3_overlay")
    
    for d in [L3_png_folder, ver_folder, L3_mask_folder, L3_clean_mask_folder, L3_overlay_folder]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(os.path.join(L3_png_folder, SAGITTAL_CLEAN)):
        generate_sagittal(input_folder, output_folder, force=False)

    whole_weights = "outputwhole/model_final.pth"
    vertebra_weights = "outputnew/model_final.pth"

    img_path = os.path.join(L3_png_folder, SAGITTAL_INPUT)
    write_log(output_folder, "L3_DETECT vertebra_infer start")
    results = process_spine_and_vertebrae(img_path, whole_weights, vertebra_weights, ver_folder)
    write_log(output_folder, f"L3_DETECT vertebra_infer done keys={list(results.keys()) if results else None}")
    
    # 复制结果到原有目录结构
    import shutil
    base_name = "sagittal_midResize_0000"
    
    # 复制 L3 mask 和 overlay
    src_mask = os.path.join(ver_folder, f"{base_name}_L3_mask.png")
    dst_mask = os.path.join(L3_mask_folder, SAGITTAL_CLEAN)
    if os.path.exists(src_mask):
        shutil.copy2(src_mask, dst_mask)
        write_log(output_folder, f"L3_DETECT copy L3 mask -> {dst_mask}")
    
    src_overlay = os.path.join(ver_folder, f"{base_name}_L3_overlay.png") 
    dst_overlay = os.path.join(L3_overlay_folder, SAGITTAL_CLEAN)
    if os.path.exists(src_overlay):
        shutil.copy2(src_overlay, dst_overlay)
        write_log(output_folder, f"L3_DETECT copy L3 overlay -> {dst_overlay}")
    
    # 清理和生成最终 overlay
    from sagit_save import clean_mask_folder, overlay_and_save
    clean_mask_folder(L3_mask_folder, L3_clean_mask_folder)
    overlay_and_save(L3_png_folder, L3_clean_mask_folder, L3_overlay_folder)
    write_log(output_folder, "L3_DETECT cleaned & overlay generated")
    
    write_log(output_folder, "L3_DETECT END")
    return {
        "sagittal_png": f"L3_png/{SAGITTAL_CLEAN}",
        "l3_mask": f"L3_clean_mask/{SAGITTAL_CLEAN}",
        "l3_overlay": f"L3_overlay/{SAGITTAL_CLEAN}",
        "auto": True
    }

def continue_after_l3(input_folder, output_folder):
    write_log(output_folder, f"CONT_AFTER_L3 START input={input_folder}")
    # 只做横断面提取和后续分割
    L3_cleaned_mask_folder = os.path.join(output_folder, "L3_clean_mask")
    mask_path = os.path.join(L3_cleaned_mask_folder, SAGITTAL_CLEAN)
    if not os.path.exists(mask_path):
        write_log(output_folder, "CONT_AFTER_L3 MISSING_L3_MASK abort")
        return {"error": "缺少 L3_clean_mask/sagittal_midResize.png，请先自动或手动上传"}
    
    slice_folder = os.path.join(output_folder, "Axisal")
    # 清理 Axisal 目录下所有 png 文件
    safe_clear_folder(slice_folder, [".png"])
    full_mask_folder = os.path.join(output_folder, "full_mask")
    clean_full_mask_folder = os.path.join(output_folder, "clean")
    full_overlay_folder = os.path.join(output_folder, "full_overlay")
    # 新增：如果 full_overlay 文件夹存在则清空
    if os.path.isdir(full_overlay_folder):
        for f in os.listdir(full_overlay_folder):
            file_path = os.path.join(full_overlay_folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)    
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
    mask = cv2.resize(mask, (volume.shape[1], volume.shape[0]), interpolation=cv2.INTER_NEAREST)
    write_log(output_folder, f"CONT_AFTER_L3 restored_mask shape={mask.shape}")

    # 横断面提取
    write_log(output_folder, "CONT_AFTER_L3 axial extraction start")
    axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, mask, x_mid, save_images=False)
    if axial_slices_numbers:
        preview = axial_slices_numbers[:2] + axial_slices_numbers[-2:]
    else:
        preview = []
    write_log(output_folder, f"CONT_AFTER_L3 axial count={len(axial_slices_numbers)} preview={preview}")
    convert_selected_slices_by_z_index(
        dicom_folder=input_folder,
        output_folder=slice_folder,
        selected_z_indices=axial_slices_numbers
    )

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

    # 只保留*_0000.png 作为 nnUNet 输入
    write_log(output_folder, "CONT_AFTER_L3 clean nnunet inputs")
    clean_nnunet_input_folder(slice_folder)

    write_log(output_folder, "CONT_AFTER_L3 psoas nnunet start")
    run_nnunet_predict_and_overlay(slice_folder, major_mask_folder, major_model_dir, major_checkpoint)
    write_log(output_folder, f"CONT_AFTER_L3 psoas nnunet done count={len(os.listdir(major_mask_folder))}")
    
    write_log(output_folder, "CONT_AFTER_L3 full nnunet start")
    run_nnunet_predict_and_overlay(slice_folder, full_mask_folder, full_model_dir, full_checkpoint)
    write_log(output_folder, f"CONT_AFTER_L3 full nnunet done count={len(os.listdir(full_mask_folder))}")

    for filename in os.listdir(slice_folder):
        if filename.endswith("_0000.png"):
            name_wo_ext = filename[:-9]
            old_path = os.path.join(slice_folder, filename)
            new_path = os.path.join(slice_folder, name_wo_ext + ".png")
            os.rename(old_path, new_path)

    write_log(output_folder, "CONT_AFTER_L3 metrics start")
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
    write_log(output_folder, "CONT_AFTER_L3 metrics done")
    write_log(output_folder, "CONT_AFTER_L3 END")
    return {"status": "ok", "message": "后续流程已完成"}

def generate_sagittal(input_folder, output_folder, force=False):
    L3_png_folder = os.path.join(output_folder, "L3_png")
    os.makedirs(L3_png_folder, exist_ok=True)

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

def clean_nnunet_input_folder(folder):
    if not os.path.isdir(folder):
        return
    for f in os.listdir(folder):
        if f.endswith(".png") and not f.endswith("_0000.png"):
            os.remove(os.path.join(folder, f))

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
                
if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    main()
