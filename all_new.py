import SimpleITK as sitk
import cv2
import os
import numpy as np
import torch
import multiprocessing as mp
from sagit_save import resize_and_save_sagittal_as_dicom, dicom_to_balanced_png
from verseg import process_spine_and_vertebrae
from extract_slice import load_mask, extract_axial_slices_from_sagittal_mask
from tar_area import run_tar_area, filter_single_mask_folder, remove_small_full, add_intersect_removed_to_filtered
from extract_slice import load_mask, extract_axial_slices_from_sagittal_mask
from extract_slice import convert_selected_slices_by_z_index

from seg import run_nnunet_predict_and_overlay
from compute import process_all
from recon import reconstruct_ct_volume, convert_binary_to_255
from majorseg import run_psoas_pipeline
from fatsp import batch_process_outer_contours, batch_split_sat_vat

SAGITTAL_BASE = "sagittal_midResize"
SAGITTAL_INPUT = SAGITTAL_BASE + "_0000.png"   # nnUNet 输入文件
SAGITTAL_CLEAN = SAGITTAL_BASE + ".png"        # 前端&手动标注&最终mask统一文件


def main(input_folder, output_folder):
    dicom_folder = input_folder
    # 所有输出目录都在 output_folder 下
    L3_png_folder = os.path.join(output_folder, "L3_png")
    ver_folder = os.path.join(output_folder, "verseg")
    slice_folder = os.path.join(output_folder, "Axisal")
    tar_area_folder = os.path.join(output_folder, "target_area")
    fat_mask_folder = os.path.join(output_folder, "fat_mask")
    fat_filtered_folder = os.path.join(output_folder, "fat_filtered")
    fat_overlay_folder = os.path.join(output_folder, "fat_overlay")
    full_mask_folder = os.path.join(output_folder, "full_mask")
    full_cleaned_folder = os.path.join(output_folder, "clean_full_mask")
    full_removed_folder = os.path.join(output_folder, "removed_small_full_mask")
    full_mask255_folder = os.path.join(output_folder, "full_255mask")
    hulls_output_dir = os.path.join(output_folder, "hulls_output")
    hulls_output_dir_new = os.path.join(output_folder, "hulls_output_new")
    full_filtered_folder = os.path.join(output_folder, "full_filtered") # 最终全肌肉mask
    full_recon_folder = os.path.join(output_folder, "full_mask_recon")
    full_overlay_folder = os.path.join(output_folder, "full_overlay") # 肌肉部分的覆盖图
    major_mask_folder = os.path.join(output_folder, "major_mask")
    major_filtered_folder = os.path.join(output_folder, "major_filtered") # 最终腰大肌mask
    major_recon_folder = os.path.join(output_folder, "major_mask_recon")
    major_overlay_folder = os.path.join(output_folder, "major_overlay")
    sat_mask_folder = os.path.join(output_folder, "SAT_mask")
    vat_mask_folder = os.path.join(output_folder, "VAT_mask")
    all_overlay_folder =  os.path.join(output_folder, "all_overlay") # 包含脂肪、肌肉的覆盖图


    # 模型路径
    tar_area_weights = "outputwholearea/model_final.pth"
    whole_weights = "outputwhole/model_final.pth"
    vertebra_weights = "outputnew/model_final.pth"
    full_model_dir="nnUNet_results/Dataset006_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    full_checkpoint="checkpoint_final.pth"
    bone_model_path = "outputbone/model_final.pth"
    psoas_model_path = "outputmajor1000/model_final.pth"

    # 1. 找中间视角的侧视图
    # Load 3D volume
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()

    volume = sitk.GetArrayFromImage(image)  # [Z, Y, X]
    spacing = image.GetSpacing()
    print("spacing:", spacing)

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
    img_path = os.path.join(L3_png_folder, SAGITTAL_INPUT)
    results = process_spine_and_vertebrae(img_path, whole_weights, vertebra_weights, ver_folder)
    L3_mask_path = results["L3_mask"]
    print("L3_mask_path:", L3_mask_path)
    mask = load_mask(L3_mask_path)
    restored_mask = cv2.resize(mask, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)

    # 3. 找对应的横切图
    # Extract corresponding axial slices
    axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, restored_mask, x_mid, save_images=False)
    print(f"[DEBUG] axial z indices (main) count={len(axial_slices_numbers)} "
          f"first/last={axial_slices_numbers[:2]} ... {axial_slices_numbers[-2:]}")
    convert_selected_slices_by_z_index(
        dicom_folder=dicom_folder,
        output_folder=slice_folder,
        mask_folder=fat_mask_folder,
        overlay_folder=fat_overlay_folder,
        selected_z_indices=axial_slices_numbers
    )
    
    # 对slice_folder中的图像进行maskrcnn，提取target_area，保存到对应文件夹
    run_tar_area(
        input_folder=slice_folder,
        output_folder=tar_area_folder,
        weights_path=tar_area_weights
    )
    # 4. 腰大肌的识别
    run_psoas_pipeline(slice_folder, major_mask_folder, bone_model_path, psoas_model_path)

    # 5. 全肌肉的识别
    run_nnunet_predict_and_overlay(slice_folder, full_mask_folder, full_model_dir, full_checkpoint)
    convert_binary_to_255(full_mask_folder, full_mask255_folder)
    # remove_small_full(full_mask_folder, full_cleaned_folder)
    remove_small_full(full_mask_folder, full_cleaned_folder, full_removed_folder)

    roi_info_folder = os.path.join(tar_area_folder, "roi_info")
    for filename in os.listdir(slice_folder):
        if filename.endswith("_0000.png"):
            name_wo_ext = filename[:-9]
            old_path = os.path.join(slice_folder, filename)
            new_path = os.path.join(slice_folder, name_wo_ext + ".png")
            os.rename(old_path, new_path)
            print(f"Renamed: {filename} → {name_wo_ext}.png")

    # 后处理部分
    filter_single_mask_folder(slice_folder, major_mask_folder, roi_info_folder, major_filtered_folder)
    filter_single_mask_folder(slice_folder, full_cleaned_folder, roi_info_folder, full_filtered_folder)
    filter_single_mask_folder(slice_folder, fat_mask_folder, roi_info_folder, fat_filtered_folder)

    # 6. 脂肪的SAT和VAT分离
    batch_process_outer_contours(full_filtered_folder, hulls_output_dir)
    add_intersect_removed_to_filtered(hulls_output_dir, full_removed_folder, full_filtered_folder)
    batch_process_outer_contours(full_filtered_folder, hulls_output_dir_new)
    batch_split_sat_vat(fat_filtered_folder, hulls_output_dir_new, sat_mask_folder, vat_mask_folder)

    # 7 三维重建及体积计算
    # 体积是分开部分的体积
    major_volume_mm3 = reconstruct_ct_volume(major_filtered_folder, major_recon_folder, spacing, visualize=False)
    full_volume_mm3 = reconstruct_ct_volume(full_filtered_folder, full_recon_folder, spacing, visualize=False)

    combo_volume_mm3 = major_volume_mm3 + full_volume_mm3

    # 6 全肌肉 + 腰大肌一起计算
    process_all(
        psoas_mask_dir=major_filtered_folder,
        full_mask_dir=full_filtered_folder,
        sat_mask_dir=sat_mask_folder,
        vat_mask_dir=vat_mask_folder,
        slice_dir=slice_folder,
        dicom_dir=dicom_folder,
        overlay_psoas_dir=major_overlay_folder,
        overlay_combo_dir=full_overlay_folder,
        overlay_all_dir=all_overlay_folder,
        major_volume_mm3=major_volume_mm3,
        combo_volume_mm3=combo_volume_mm3
    )

def clean_nnunet_input_folder(folder):
    if not os.path.isdir(folder):
        return
    for f in os.listdir(folder):
        if f.endswith(".png") and not f.endswith("_0000.png"):
            os.remove(os.path.join(folder, f))

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

def l3_detect(input_folder, output_folder):
    L3_png_folder = os.path.join(output_folder, "L3_png")
    ver_folder = os.path.join(output_folder, "verseg")

    for d in [L3_png_folder, ver_folder]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(os.path.join(L3_png_folder, SAGITTAL_CLEAN)):
        generate_sagittal(input_folder, output_folder, force=False)

    whole_weights = "outputwhole/model_final.pth"
    vertebra_weights = "outputnew/model_final.pth"

    img_path = os.path.join(L3_png_folder, SAGITTAL_INPUT)
    results = process_spine_and_vertebrae(img_path, whole_weights, vertebra_weights, ver_folder)
    L3_mask_path = results["L3_mask"]
    print("L3_mask_path:", L3_mask_path)








def continue_after_l3(input_folder, output_folder):
    dicom_folder = input_folder
    L3_png_folder = os.path.join(output_folder, "L3_png")
    ver_folder = os.path.join(output_folder, "verseg")
    slice_folder = os.path.join(output_folder, "Axisal")
    tar_area_folder = os.path.join(output_folder, "target_area")
    fat_mask_folder = os.path.join(output_folder, "fat_mask")
    fat_filtered_folder = os.path.join(output_folder, "fat_filtered")
    fat_overlay_folder = os.path.join(output_folder, "fat_overlay")
    full_mask_folder = os.path.join(output_folder, "full_mask")
    full_cleaned_folder = os.path.join(output_folder, "clean_full_mask")
    full_mask255_folder = os.path.join(output_folder, "full_255mask")
    hulls_output_dir = os.path.join(output_folder, "hulls_output")
    full_filtered_folder = os.path.join(output_folder, "full_filtered") # 最终全肌肉mask
    full_recon_folder = os.path.join(output_folder, "full_mask_recon")
    full_overlay_folder = os.path.join(output_folder, "full_overlay") # 肌肉部分的覆盖图
    major_mask_folder = os.path.join(output_folder, "major_mask")
    major_filtered_folder = os.path.join(output_folder, "major_filtered") # 最终腰大肌mask
    major_recon_folder = os.path.join(output_folder, "major_mask_recon")
    major_overlay_folder = os.path.join(output_folder, "major_overlay")
    sat_mask_folder = os.path.join(output_folder, "SAT_mask")
    vat_mask_folder = os.path.join(output_folder, "VAT_mask")
    all_overlay_folder =  os.path.join(output_folder, "all_overlay") # 包含脂肪、肌肉的覆盖图

    tar_area_weights = "outputwholearea/model_final.pth"
    full_model_dir="nnUNet_results/Dataset006_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d"
    full_checkpoint="checkpoint_final.pth"
    bone_model_path = "outputbone/model_final.pth"
    psoas_model_path = "outputmajor1000/model_final.pth"

    # 读取 DICOM
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(input_folder)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    volume = sitk.GetArrayFromImage(image)
    orig_height, orig_width = volume.shape[1], volume.shape[2]
    x_mid = volume.shape[2] // 2
    spacing = image.GetSpacing()


    spacing_z = spacing[2]  # height direction
    spacing_y = spacing[1]  # width direction

    img_path = os.path.join(L3_png_folder, SAGITTAL_INPUT)
    label = "L3"
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    L3_mask_path = os.path.join(ver_folder, f"{base_name}_{label}_mask.png")

    mask = load_mask(L3_mask_path)
    restored_mask = cv2.resize(mask, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)

    print("DEBUG: restored mask shape:", mask.shape)
    # Extract corresponding axial slices
    axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, restored_mask, x_mid, save_images=False)
    print(f"[DEBUG] axial z indices (main) count={len(axial_slices_numbers)} "
          f"first/last={axial_slices_numbers[:2]} ... {axial_slices_numbers[-2:]}")
    convert_selected_slices_by_z_index(
        dicom_folder=dicom_folder,
        output_folder=slice_folder,
        mask_folder=fat_mask_folder,
        overlay_folder=fat_overlay_folder,
        selected_z_indices=axial_slices_numbers
    )
    
    # 对slice_folder中的图像进行maskrcnn，提取target_area，保存到对应文件夹
    run_tar_area(
        input_folder=slice_folder,
        output_folder=tar_area_folder,
        weights_path=tar_area_weights
    )
    # 4. 腰大肌的识别
    run_psoas_pipeline(slice_folder, major_mask_folder, bone_model_path, psoas_model_path)

    # 5. 全肌肉的识别
    run_nnunet_predict_and_overlay(slice_folder, full_mask_folder, full_model_dir, full_checkpoint)
    convert_binary_to_255(full_mask_folder, full_mask255_folder)
    remove_small_full(full_mask_folder, full_cleaned_folder)

    roi_info_folder = os.path.join(tar_area_folder, "roi_info")
    for filename in os.listdir(slice_folder):
        if filename.endswith("_0000.png"):
            name_wo_ext = filename[:-9]
            old_path = os.path.join(slice_folder, filename)
            new_path = os.path.join(slice_folder, name_wo_ext + ".png")
            os.rename(old_path, new_path)
            print(f"Renamed: {filename} → {name_wo_ext}.png")

    # 后处理部分
    filter_single_mask_folder(slice_folder, major_mask_folder, roi_info_folder, major_filtered_folder)
    filter_single_mask_folder(slice_folder, full_cleaned_folder, roi_info_folder, full_filtered_folder)
    filter_single_mask_folder(slice_folder, fat_mask_folder, roi_info_folder, fat_filtered_folder)

    # 6. 脂肪的SAT和VAT分离
    batch_process_masks(full_filtered_folder, hulls_output_dir)    
    batch_split_sat_vat(fat_filtered_folder, hulls_output_dir, sat_mask_folder, vat_mask_folder)

    # 7 三维重建及体积计算
    # 体积是分开部分的体积
    major_volume_mm3 = reconstruct_ct_volume(major_filtered_folder, major_recon_folder, spacing, visualize=False)
    full_volume_mm3 = reconstruct_ct_volume(full_filtered_folder, full_recon_folder, spacing, visualize=False)

    combo_volume_mm3 = major_volume_mm3 + full_volume_mm3

    # 6 全肌肉 + 腰大肌一起计算
    process_all(
        psoas_mask_dir=major_filtered_folder,
        full_mask_dir=full_filtered_folder,
        sat_mask_dir=sat_mask_folder,
        vat_mask_dir=vat_mask_folder,
        slice_dir=slice_folder,
        dicom_dir=dicom_folder,
        overlay_psoas_dir=major_overlay_folder,
        overlay_combo_dir=full_overlay_folder,
        overlay_all_dir=all_overlay_folder,
        major_volume_mm3=major_volume_mm3,
        combo_volume_mm3=combo_volume_mm3
    )



if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    main("1411637", "Novnn_1411637")