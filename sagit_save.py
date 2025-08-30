import pydicom
from pydicom.uid import generate_uid
import numpy as np
from PIL import Image
import os
import cv2

# 函数：resize and save 中间切片为DICOM
def resize_and_save_sagittal_as_dicom(
    sagittal_slice, spacing, reference_dicom_path, output_path="sagittal_midResize.dcm"
):
    # Step 1: Compute spacing ratio
    spacing_z = spacing[2]  # height (Z)
    spacing_y = spacing[1]  # width  (Y)
    scale_ratio = spacing_z / spacing_y

    print("Original shape:", sagittal_slice.shape)
    print("Spacing Z/Y:", spacing_z, spacing_y, "→ scale ratio:", scale_ratio)

    # Step 2: Normalize and resize for physical correctness
    pil_img = Image.fromarray(sagittal_slice)
    orig_height, orig_width = sagittal_slice.shape
    new_height = int(orig_height * scale_ratio)

    pil_resized = pil_img.resize((orig_width, new_height), resample=Image.BILINEAR)
    resized_array = np.array(pil_resized).astype(np.int16)

    # Step 3: Load reference DICOM for metadata
    ds = pydicom.dcmread(reference_dicom_path)
    ds.Rows, ds.Columns = resized_array.shape
    ds.PixelData = resized_array.tobytes()

    # Step 4: Update DICOM metadata
    ds.PixelSpacing = [str(spacing_z), str(spacing_y)]
    ds.SliceThickness = str(spacing_z)
    ds.BitsStored = 16
    ds.BitsAllocated = 16
    ds.HighBit = 15
    ds.SamplesPerPixel = 1
    ds.PixelRepresentation = 1

    ds.SOPInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesDescription = "Resized Sagittal"

    # Step 5: Save
    ds.save_as(output_path)
    return output_path


def dicom_to_balanced_png(dicom_path, out_dir, scale_ratio,
                          default_center=None, default_width=None):
    os.makedirs(out_dir, exist_ok=True)

    # 读取 DICOM
    ds = pydicom.dcmread(dicom_path)
    pixel_array = ds.pixel_array.astype(np.float32)

    pixel_array = pixel_array * 1 - 100

    center_val = ds.get("WindowCenter", np.mean(pixel_array))
    width_val = ds.get("WindowWidth", np.max(pixel_array) - np.min(pixel_array))

    if isinstance(center_val, pydicom.multival.MultiValue):
        center_val = center_val[0]
    if isinstance(width_val, pydicom.multival.MultiValue):
        width_val = width_val[0]

    center = default_center if default_center is not None else float(center_val)
    width = default_width if default_width is not None else float(width_val)

    # 窗宽窗位裁剪
    min_val = center - width / 2
    max_val = center + width / 2
    hu_clipped = np.clip(pixel_array, min_val, max_val)

    # 归一化到 0-255
    hu_normalized = ((hu_clipped - min_val) / (max_val - min_val)) * 255.0
    hu_uint8 = hu_normalized.astype(np.uint8)
    hu_uint8[hu_uint8 == 0] = 255
    img = Image.fromarray(hu_uint8)

    # 保存文件（命名和 dicom 一致，只改扩展名为 .png）
    base = os.path.splitext(os.path.basename(dicom_path))[0]
    out_path = os.path.join(out_dir, f"{base}_0000.png")
    img.save(out_path)

    return out_path

def overlay_and_save(img_dir, mask_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    for fname in os.listdir(mask_dir):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        # mask 文件路径
        mask_path = os.path.join(mask_dir, fname)

        # 原图文件名：比 mask 多一个 "_0000"
        name, ext = os.path.splitext(fname)
        img_name = f"{name}_0000{ext}"
        img_path = os.path.join(img_dir, img_name)

        if not os.path.exists(img_path):
            print(f"[跳过] 找不到对应原图: {img_name}")
            continue

        # 读取
        img = cv2.imread(img_path)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if img is None or mask is None:
            print(f"[跳过] 读取失败: {fname}")
            continue

        # overlay
        overlay = img.copy()
        overlay[mask > 0] = (0, 255, 0)  # 绿色

        # 输出文件路径（沿用 mask 文件名）
        out_path = os.path.join(out_dir, fname)
        cv2.imwrite(out_path, overlay)
        print(f"[保存] {out_path}")

def keep_largest_component(mask):

    if mask is None:
        return None
    binary = (mask > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels <= 1:
        return mask
    largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return (labels == largest_label).astype(np.uint8) * 255


def clean_mask_folder(src_mask_dir, dst_mask_dir):
    os.makedirs(dst_mask_dir, exist_ok=True)

    for fname in os.listdir(src_mask_dir):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        src_path = os.path.join(src_mask_dir, fname)
        dst_path = os.path.join(dst_mask_dir, fname)

        mask = cv2.imread(src_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            print(f"[跳过] 读取失败: {src_path}")
            continue

        cleaned = keep_largest_component(mask)
        cv2.imwrite(dst_path, cleaned)
        print(f"[保存 cleaned] {dst_path}")



