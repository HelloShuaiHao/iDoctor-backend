import os
import shutil
import numpy as np
import pydicom
from pydicom.uid import generate_uid
from PIL import Image
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


def dicom_to_balanced_png(dcm_path, out_dir, scale_ratio, base_name="sagittal_midResize"):
    """
    生成两张：
      base_name_0000.png (模型输入)
      base_name.png      (干净图，前端显示与手动标注)
    返回 (input_png_path, clean_png_path)
    """
    os.makedirs(out_dir, exist_ok=True)
    ds = pydicom.dcmread(dcm_path)
    arr = ds.pixel_array.astype(np.float32)

    # 简单窗宽窗位处理
    center = np.mean(arr)
    width = np.max(arr) - np.min(arr)
    vmin = center - width / 2
    vmax = center + width / 2
    arr = np.clip(arr, vmin, vmax)
    arr = ((arr - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    # 反相背景处理
    arr[arr == 0] = 255

    img = Image.fromarray(arr)
    input_name = f"{base_name}_0000.png"
    clean_name = f"{base_name}.png"
    input_path = os.path.join(out_dir, input_name)
    clean_path = os.path.join(out_dir, clean_name)
    img.save(input_path)
    shutil.copy(input_path, clean_path)
    return input_path, clean_path

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



