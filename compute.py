import os
import re
import glob
import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
import SimpleITK as sitk

def load_dicom_hu(dicom_path):
    if dicom_path.lower().endswith(".dcm.pk"):
        itk_img = sitk.ReadImage(dicom_path)
        image = sitk.GetArrayFromImage(itk_img)[0]
        spacing = itk_img.GetSpacing()
        if len(spacing) >= 2:
            pixel_size_mm = float(spacing[1])  # ITK: spacing=(x, y, z)
        else:
            pixel_size_mm = 1.0 
        hu_image = image
    else:
        ds = pydicom.dcmread(dicom_path)
        image = ds.pixel_array
        spacing = ds.PixelSpacing
        pixel_size_mm = float(spacing[0])
        hu_image = apply_modality_lut(image, ds)
    return hu_image, pixel_size_mm

def compute_mask_hu_statistics(dicom_path, mask_bool):
    hu_image, pixel_size_mm = load_dicom_hu(dicom_path)
    if mask_bool.dtype != bool:
        mask_bool = mask_bool.astype(bool)
    if not np.any(mask_bool):
        return {
            "pixels": 0, "hu_mean": np.nan, "hu_min": np.nan, "hu_max": np.nan,
            "hu_sum": np.nan, "area_mm2": 0.0
        }
    hu_values = hu_image[mask_bool]
    area_mm2 = float(np.sum(mask_bool)) * (pixel_size_mm ** 2)
    return {
        "pixels": int(np.sum(mask_bool)),
        "hu_mean": float(np.round(np.mean(hu_values), 2)),
        "hu_min": float(np.round(np.min(hu_values), 2)),
        "hu_max": float(np.round(np.max(hu_values), 2)),
        "hu_sum": float(np.round(np.sum(hu_values), 2)),
        "area_mm2": float(np.round(area_mm2, 2))
    }


def clean_full_mask(mask_gray, area_thresh=1000, area_ratio_thresh=0.05, morph_ksize=3, morph_iters=1):
    bin_ = (mask_gray > 0).astype(np.uint8)
    if np.sum(bin_) == 0:
        return np.zeros_like(mask_gray, dtype=np.uint8)

    # 连通域
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_, connectivity=8)
    if num_labels <= 1:
        cleaned = (bin_ * 255).astype(np.uint8)
    else:
        areas = stats[1:, cv2.CC_STAT_AREA]
        max_area = areas.max() if areas.size > 0 else 0
        keep = np.zeros_like(bin_)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= area_thresh and (max_area == 0 or area >= max_area * area_ratio_thresh):
                keep[labels == i] = 1
        cleaned = (keep * 255).astype(np.uint8)

    if morph_ksize and morph_iters and morph_iters > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_ksize, morph_ksize))
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, k, iterations=morph_iters)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, k, iterations=morph_iters)

    return cleaned

def overlay_mask_on_image(image_bgr, mask_uint8, color=(0, 255, 0), alpha=0.5):
    if image_bgr is None:
        return None
    if len(image_bgr.shape) == 2 or image_bgr.shape[2] == 1:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    overlay = image_bgr.copy()
    colored = np.zeros_like(image_bgr)
    colored[mask_uint8 == 255] = color
    out = cv2.addWeighted(overlay, 1 - alpha, colored, alpha, 0)
    return out

def overlay_multi_masks(image_bgr, combo_mask, sat_mask, vat_mask,
                        combo_color=(0,255,0), sat_color=(0,255,255), vat_color=(255,0,255),
                        alpha=0.5):

    if len(image_bgr.shape) == 2:
        image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)

    overlay = image_bgr.copy()
    color_layer = np.zeros_like(image_bgr)

    H, W = combo_mask.shape

    idx = vat_mask == 255
    color_layer[idx] = vat_color

    idx = sat_mask == 255
    color_layer[idx] = sat_color

    idx = combo_mask == 255
    color_layer[idx] = combo_color  # <-- 永远最高优先级

    out = cv2.addWeighted(overlay, 1 - alpha, color_layer, alpha, 0)
    return out


# 增加脂肪的计算
def process_all( 
    psoas_mask_dir,
    full_mask_dir,
    sat_mask_dir,
    vat_mask_dir,
    slice_dir,
    dicom_dir,
    overlay_psoas_dir,
    overlay_combo_dir,
    overlay_all_dir,
    major_volume_mm3=None,
    combo_volume_mm3=None,
):
    os.makedirs(overlay_psoas_dir, exist_ok=True)
    os.makedirs(overlay_combo_dir, exist_ok=True)
    os.makedirs(overlay_all_dir, exist_ok=True)

    pattern="*.png"
    overlay_alpha=0.5
    
    img_paths = sorted(glob.glob(os.path.join(slice_dir, pattern)))
    if not img_paths:
        print("[警告] 未在 slice_dir 中找到任何图片：", slice_dir)
        return

    dicom_files = sorted([
        f for f in os.listdir(dicom_dir)
        if not f.startswith("._") and f.lower().endswith((".dcm", ".dcm.pk"))
    ])
    
    results = []
    valid_items = []

    for img_path in tqdm(img_paths, desc="处理中"):
        fname = os.path.basename(img_path)
        psoas_path = os.path.join(psoas_mask_dir, fname)
        full_path  = os.path.join(full_mask_dir,  fname)
        sat_path   = os.path.join(sat_mask_dir,   fname)
        vat_path   = os.path.join(vat_mask_dir,   fname)


        if not (os.path.exists(psoas_path) and os.path.exists(full_path) and os.path.exists(sat_path) and os.path.exists(vat_path)):
            print(f"[跳过] 缺少部分 mask：{fname}")
            continue

        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        psoas_mask = cv2.imread(psoas_path, cv2.IMREAD_GRAYSCALE)
        full_mask  = cv2.imread(full_path,  cv2.IMREAD_GRAYSCALE)
        sat_mask   = cv2.imread(sat_path,   cv2.IMREAD_GRAYSCALE)
        vat_mask   = cv2.imread(vat_path,   cv2.IMREAD_GRAYSCALE)
        if img is None or psoas_mask is None or full_mask is None or sat_mask is None or vat_mask is None:
            print(f"[跳过] 读取失败：{fname}")
            continue

        psoas_bin = (psoas_mask > 0).astype(np.uint8) * 255
        full_bin  = (full_mask  > 0).astype(np.uint8) * 255
        sat_bin   = (sat_mask   > 0).astype(np.uint8) * 255
        vat_bin   = (vat_mask   > 0).astype(np.uint8) * 255
        

        # combo = psoas + full
        combo_mask = np.maximum(psoas_bin, full_bin)

        # 覆盖图
        psoas_overlay = overlay_mask_on_image(img, psoas_bin, color=(0, 0, 255), alpha=overlay_alpha)
        combo_overlay = overlay_mask_on_image(img, combo_mask, color=(0, 255, 0), alpha=overlay_alpha)

        multi_overlay = overlay_multi_masks(
            img,
            combo_mask=combo_mask,
            sat_mask=sat_bin,
            vat_mask=vat_bin,
            combo_color=(0,255,0),
            sat_color=(0,255,255),
            vat_color=(255,0,255),
            alpha=overlay_alpha
        )

        # 保存
        if psoas_overlay is not None:
            cv2.imwrite(os.path.join(overlay_psoas_dir, fname), psoas_overlay)
        if combo_overlay is not None:
            cv2.imwrite(os.path.join(overlay_combo_dir, fname), combo_overlay)
        if multi_overlay is not None:
            cv2.imwrite(os.path.join(overlay_all_dir, fname), multi_overlay)

        # ===================== DICOM HU 统计 ====================
        match = re.search(r'(\d+)', fname)
        if match:
            slice_id = match.group(1).zfill(3)
            dicom_match = next((f for f in dicom_files if slice_id in f), None)

            if dicom_match:
                dicom_path = os.path.join(dicom_dir, dicom_match)
                stat_psoas = compute_mask_hu_statistics(dicom_path, psoas_bin == 255)
                stat_combo = compute_mask_hu_statistics(dicom_path, combo_mask == 255)
                stat_sat   = compute_mask_hu_statistics(dicom_path, sat_bin  == 255)
                stat_vat   = compute_mask_hu_statistics(dicom_path, vat_bin  == 255)

            else:
                # DICOM 未找到 → 统一空统计
                empty_stat = {
                    "pixels":0,"hu_mean":np.nan,"hu_min":np.nan,"hu_max":np.nan,
                    "hu_sum":np.nan,"area_mm2":0.0
                }
                stat_psoas = stat_combo = stat_sat = stat_vat = empty_stat

        else:
            # 文件名无 slice id → 统一空统计
            empty_stat = {
                "pixels":0,"hu_mean":np.nan,"hu_min":np.nan,"hu_max":np.nan,
                "hu_sum":np.nan,"area_mm2":0.0
            }
            stat_psoas = stat_combo = stat_sat = stat_vat = empty_stat

        # 记录三类区域
        row = {
            "filename": fname,

            # ------------ psoas --------------
            "psoas_pixels":  stat_psoas["pixels"],
            "psoas_hu_mean": stat_psoas["hu_mean"],
            "psoas_hu_min":  stat_psoas["hu_min"],
            "psoas_hu_max":  stat_psoas["hu_max"],
            "psoas_hu_sum":  stat_psoas["hu_sum"],
            "psoas_area_mm2":stat_psoas["area_mm2"],

            # ------------ combo --------------
            "combo_pixels":  stat_combo["pixels"],
            "combo_hu_mean": stat_combo["hu_mean"],
            "combo_hu_min":  stat_combo["hu_min"],
            "combo_hu_max":  stat_combo["hu_max"],
            "combo_hu_sum":  stat_combo["hu_sum"],
            "combo_area_mm2":stat_combo["area_mm2"],

            # ------------ SAT --------------
            "sat_pixels":  stat_sat["pixels"],
            "sat_hu_mean": stat_sat["hu_mean"],
            "sat_hu_min":  stat_sat["hu_min"],
            "sat_hu_max":  stat_sat["hu_max"],
            "sat_hu_sum":  stat_sat["hu_sum"],
            "sat_area_mm2":stat_sat["area_mm2"],

            # ------------ VAT --------------
            "vat_pixels":  stat_vat["pixels"],
            "vat_hu_mean": stat_vat["hu_mean"],
            "vat_hu_min":  stat_vat["hu_min"],
            "vat_hu_max":  stat_vat["hu_max"],
            "vat_hu_sum":  stat_vat["hu_sum"],
            "vat_area_mm2":stat_vat["area_mm2"],

        }

        results.append(row)
        valid_items.append(fname)

    if not results:
        print("[完成] 没有可用样本，未生成结果。")
        return

    df = pd.DataFrame(results)

    # ==================== 仅对 psoas + combo 做体积质量 ====================
    mean_psoas_HU = df["psoas_hu_mean"].mean(skipna=True)
    mean_combo_HU = df["combo_hu_mean"].mean(skipna=True)

    rho_psoas = 1 + 0.001 * mean_psoas_HU
    rho_combo = 1 + 0.001 * mean_combo_HU

    vol_psoas_cm3 = major_volume_mm3 / 1000.0 if major_volume_mm3 else np.nan
    vol_combo_cm3 = combo_volume_mm3 / 1000.0 if combo_volume_mm3 else np.nan

    mass_psoas_g = vol_psoas_cm3 * rho_psoas
    mass_combo_g = vol_combo_cm3 * rho_combo

    df["major_volume_mm3"] = major_volume_mm3
    df["full_volume_mm3"]  = combo_volume_mm3
    df["mass_psoas_g"] = mass_psoas_g
    df["mass_combo_g"] = mass_combo_g

    # 输出 csv
    csv_path = os.path.join(overlay_combo_dir, "hu_statistics.csv")
    df.to_csv(csv_path, index=False)

    # 中间 slice
    mid_idx = len(valid_items) // 2
    mid_name = valid_items[mid_idx]
    df["is_middle"] = df["filename"].eq(mid_name)
    df[df["is_middle"]].to_csv(os.path.join(overlay_combo_dir, "hu_statistics_middle_only.csv"), index=False)

    print(f"[完成] 共处理 {len(valid_items)} 张。")
    print(f"[中间张] 文件名：{mid_name}")
