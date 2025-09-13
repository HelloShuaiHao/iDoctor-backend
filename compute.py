import os
import re
import glob
import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut

def load_dicom_hu(dicom_path):
    ds = pydicom.dcmread(dicom_path)
    image = ds.pixel_array
    spacing = ds.PixelSpacing  # [row_spacing_mm, col_spacing_mm]
    pixel_size_mm = float(spacing[0])  # 通常行列一致
    hu_image = apply_modality_lut(image, ds)
    return hu_image, pixel_size_mm

def compute_mask_hu_statistics(dicom_path, mask_bool):
    hu_image, pixel_size_mm = load_dicom_hu(dicom_path)
    # 可以匹配看mask对应的HU值
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

# # 过滤HU值
# def compute_mask_hu_statistics(dicom_path, mask_bool):
#     hu_image, pixel_size_mm = load_dicom_hu(dicom_path)

#     if mask_bool.dtype != bool:
#         mask_bool = mask_bool.astype(bool)
#     if not np.any(mask_bool):
#         return {
#             "pixels": 0, "hu_mean": np.nan, "hu_min": np.nan, "hu_max": np.nan,
#             "hu_sum": np.nan, "area_mm2": 0.0
#         }

#     hu_values = hu_image[mask_bool]

#     # [0, 100]
#     hu_values = hu_values[(hu_values >= 0) & (hu_values <= 100)]

#     if len(hu_values) == 0:
#         return {
#             "pixels": 0, "hu_mean": np.nan, "hu_min": np.nan, "hu_max": np.nan,
#             "hu_sum": np.nan, "area_mm2": 0.0
#         }

#     area_mm2 = float(len(hu_values)) * (pixel_size_mm ** 2)

#     return {
#         "pixels": int(len(hu_values)),
#         "hu_mean": float(np.round(np.mean(hu_values), 2)),
#         "hu_min": float(np.round(np.min(hu_values), 2)),
#         "hu_max": float(np.round(np.max(hu_values), 2)),
#         "hu_sum": float(np.round(np.sum(hu_values), 2)),
#         "area_mm2": float(np.round(area_mm2, 2))
#     }


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

def process_all(
    psoas_mask_dir,
    full_mask_dir,
    slice_dir,
    dicom_dir,
    overlay_psoas_dir,
    overlay_combo_dir,
    clean_full_mask_dir,
    pattern="*.png",
    area_thresh=1000,
    area_ratio_thresh=0.05,
    morph_ksize=3,
    morph_iters=1,
    overlay_alpha=0.5
):
    os.makedirs(overlay_psoas_dir, exist_ok=True)
    os.makedirs(overlay_combo_dir, exist_ok=True)
    os.makedirs(clean_full_mask_dir, exist_ok=True)


    img_paths = sorted(glob.glob(os.path.join(slice_dir, pattern)))
    if not img_paths:
        print("[警告] 未在 slice_dir 中找到任何图片：", slice_dir)
        return

    # dicom_files = sorted(os.listdir(dicom_dir))
    dicom_files = sorted([f for f in os.listdir(dicom_dir) if f.lower().endswith((".dcm", ".dcm.pk"))])

    results = []
    valid_items = []

    for img_path in tqdm(img_paths, desc="处理中"):
        fname = os.path.basename(img_path)
        psoas_path = os.path.join(psoas_mask_dir, fname)
        full_path  = os.path.join(full_mask_dir,  fname)

        if not os.path.exists(psoas_path):
            print(f"[跳过] 缺少腰大肌 mask：{psoas_path}")
            continue
        if not os.path.exists(full_path):
            print(f"[跳过] 缺少全肌肉 mask：{full_path}")
            continue

        # 读入
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        psoas_mask = cv2.imread(psoas_path, cv2.IMREAD_GRAYSCALE)
        full_mask  = cv2.imread(full_path,  cv2.IMREAD_GRAYSCALE)
        if img is None or psoas_mask is None or full_mask is None:
            print(f"[跳过] 读取失败：{fname}")
            continue

        # --- A) psoas 参数（未经清洗，仅 psoas） ---
        psoas_bin = (psoas_mask > 0).astype(np.uint8) * 255

        # full 清洗
        full_clean = clean_full_mask(
            full_mask,
            area_thresh=area_thresh,
            area_ratio_thresh=area_ratio_thresh,
            morph_ksize=morph_ksize,
            morph_iters=morph_iters
        )
        cv2.imwrite(os.path.join(clean_full_mask_dir, fname), full_clean)

        # 合并
        combo_mask = np.maximum(psoas_bin, full_clean)

        # --- 覆盖图 ---
        psoas_overlay = overlay_mask_on_image(img, psoas_bin, color=(0, 0, 255), alpha=overlay_alpha)
        combo_overlay = overlay_mask_on_image(img, combo_mask, color=(0, 255, 0), alpha=overlay_alpha)

        psoas_overlay_path = os.path.join(overlay_psoas_dir, fname)
        combo_overlay_path = os.path.join(overlay_combo_dir, fname)
        if psoas_overlay is not None:
            cv2.imwrite(psoas_overlay_path, psoas_overlay)
        if combo_overlay is not None:
            cv2.imwrite(combo_overlay_path, combo_overlay)

        # --- DICOM ---
        match = re.search(r'(\d+)', fname)
        if match:
            slice_id = match.group(1).zfill(3)
            dicom_match = next((f for f in dicom_files if slice_id in f), None)
            if dicom_match:
                dicom_path = os.path.join(dicom_dir, dicom_match)
                stat_psoas = compute_mask_hu_statistics(dicom_path, psoas_bin == 255)
                stat_combo = compute_mask_hu_statistics(dicom_path, combo_mask == 255)
            else:
                stat_psoas = {"pixels":0,"hu_mean":np.nan,"hu_min":np.nan,"hu_max":np.nan,"hu_sum":np.nan,"area_mm2":0.0,"error":"No matching DICOM"}
                stat_combo = stat_psoas.copy()
        else:
            stat_psoas = {"pixels":0,"hu_mean":np.nan,"hu_min":np.nan,"hu_max":np.nan,"hu_sum":np.nan,"area_mm2":0.0,"error":"Filename missing ID"}
            stat_combo = stat_psoas.copy()

        row = {
            "filename": fname,
            # psoas
            "psoas_pixels": stat_psoas.get("pixels"),
            "psoas_hu_mean": stat_psoas.get("hu_mean"),
            "psoas_hu_min": stat_psoas.get("hu_min"),
            "psoas_hu_max": stat_psoas.get("hu_max"),
            "psoas_hu_sum": stat_psoas.get("hu_sum"),
            "psoas_area_mm2": stat_psoas.get("area_mm2"),
            # combo
            "combo_pixels": stat_combo.get("pixels"),
            "combo_hu_mean": stat_combo.get("hu_mean"),
            "combo_hu_min": stat_combo.get("hu_min"),
            "combo_hu_max": stat_combo.get("hu_max"),
            "combo_hu_sum": stat_combo.get("hu_sum"),
            "combo_area_mm2": stat_combo.get("area_mm2"),
        }
        results.append(row)
        valid_items.append(fname)

    if not results:
        print("[完成] 没有可用样本，未生成结果。")
        return

    df = pd.DataFrame(results)
    # 计算中间张
    mid_idx = len(valid_items) // 2
    mid_name = valid_items[mid_idx]

    df["is_middle"] = df["filename"].eq(mid_name)

    src1 = os.path.join(overlay_psoas_dir, mid_name)
    src2 = os.path.join(overlay_combo_dir, mid_name)
    base, ext = os.path.splitext(mid_name)
    dst1 = os.path.join(overlay_psoas_dir, f"{base}_middle{ext}")
    dst2 = os.path.join(overlay_combo_dir, f"{base}_middle{ext}")

    if os.path.exists(src1):
        img1 = cv2.imread(src1, cv2.IMREAD_UNCHANGED)
        if img1 is not None:
            cv2.imwrite(dst1, img1)
    if os.path.exists(src2):
        img2 = cv2.imread(src2, cv2.IMREAD_UNCHANGED)
        if img2 is not None:
            cv2.imwrite(dst2, img2)

    csv_path = os.path.join(overlay_combo_dir, "hu_statistics.csv")
    df.to_csv(csv_path, index=False)

    # 输出中间张
    mid_csv = os.path.join(overlay_combo_dir, "hu_statistics_middle_only.csv")
    df[df["is_middle"]].to_csv(mid_csv, index=False)

    print(f"[完成] 共处理 {len(valid_items)} 张。")
    print(f"[中间张] 文件名：{mid_name}")
    print(f"[保存] 统计表：{csv_path}")
    print(f"[保存] 中间张参数：{mid_csv}")
    print(f"[保存] 中间张覆盖图：\n  - {dst1}\n  - {dst2}")



# if __name__ == "__main__":
#     # 替换为你的真实路径
#     psoas_mask_dir = "/path/to/psoas_masks"
#     full_mask_dir  = "/path/to/full_masks"
#     slice_dir      = "/path/to/slices"
#     dicom_dir      = "/path/to/dicoms"
#     overlay_psoas_dir = "/path/to/output_overlay_psoas"
#     overlay_combo_dir = "/path/to/output_overlay_combo"
#     clean_full_mask_dir = "/path/to/output_clean_full"

#     process_all(
#         psoas_mask_dir=psoas_mask_dir,
#         full_mask_dir=full_mask_dir,
#         slice_dir=slice_dir,
#         dicom_dir=dicom_dir,
#         overlay_psoas_dir=overlay_psoas_dir,
#         overlay_combo_dir=overlay_combo_dir,
#         clean_full_mask_dir=clean_full_mask_dir,
#         pattern="*.png",              # 如为 .jpg 可改成 *.jpg
#         area_thresh=1000,            # 最小绝对面积阈值（像素）
#         area_ratio_thresh=0.05,       # 相对最大连通域的比例阈值（保留 ≥5% 最大块）
#         morph_ksize=3,                # 形态学核
#         morph_iters=1,                # 形态学迭代次数
#         overlay_alpha=0.5             # 覆盖透明度
#     )
