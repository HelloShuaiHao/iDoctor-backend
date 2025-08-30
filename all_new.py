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

def main():
    # 输出目录
    dicom_folder = "1504425"
    # L3相关
    L3_png_folder = f"L3_png_{dicom_folder}"
    L3_mask_folder = f"L3_mask_{dicom_folder}"
    L3_cleaned_mask_folder = f"L3_clean_mask_{dicom_folder}"
    L3_overlay_folder = f"L3_overlay_{dicom_folder}"  # 需要展示在前端
    # 横切图
    slice_folder = f"Axisal_{dicom_folder}"
    # 肌肉分割
    full_mask_folder = f"full_mask_{dicom_folder}"
    clean_full_mask_folder = f"clean_{dicom_folder}"
    full_overlay_folder = f"full_overlay_{dicom_folder}" # 展示在前端
    major_mask_folder = f"major_mask_{dicom_folder}"
    major_overlay_folder = f"major_overlay_{dicom_folder}" # 展示在前端

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


if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    main()