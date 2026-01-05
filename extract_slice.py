import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import os
import cv2
# === Step 1: Load DICOM Series into Volume ===
def load_dicom_series(folder_path):
    dicom_files = [
        pydicom.dcmread(os.path.join(folder_path, f))
        for f in os.listdir(folder_path) if f.lower().endswith((".dcm", ".dcm.pk"))
    ]
    dicom_files.sort(key=lambda ds: float(ds.ImagePositionPatient[2]))  # sort by Z

    volume = np.stack([apply_modality_lut(ds.pixel_array, ds) for ds in dicom_files])
    return volume, dicom_files

# === Step 2: Create or Load a Binary Mask on a Sagittal Slice ===
def load_mask(mask_path):
    mask = np.array(Image.open(mask_path).convert("L"))
    unique_values = np.unique(mask)

    if 255 in unique_values:
        mask_binary = (mask == 255).astype(np.uint8)
    else:
        print(f"No foreground (255) found in {mask_path}")
        mask_binary = np.zeros_like(mask, dtype=np.uint8)

    return mask_binary

# === Step 3: Extract Axial Slices Intersecting the Sagittal Mask ===
def extract_axial_slices_from_sagittal_mask(volume, mask, x_idx, save_images=False):
    # mask = np.array(mask)
    axial_slices = []
    axial_slice_numbers = []
    print("DEBUG: type(mask):", type(mask))
    print("DEBUG: shape(mask):", getattr(mask, "shape", "No shape"))

    for z in range(mask.shape[0]):  # loop over Z (slices)
        for y in range(mask.shape[1]):  # loop over Y (rows)
            if mask[z, y]:  # if mask is active
                axial_slice = volume[z, :, :]
                axial_slices.append((z, y, axial_slice))
                axial_slice_numbers.append(z)

                if save_images:
                    plt.imshow(axial_slice, cmap='bone')
                    plt.scatter([x_idx], [y], color='red', s=30)
                    plt.title(f"Axial Slice Z={z}, Y={y}, X={x_idx}")
                    plt.axis('off')
                    plt.savefig(f"axial_z{z}_x{x_idx}_y{y}.png", bbox_inches='tight', pad_inches=0)
                    plt.close()
                break  # move to next Z slice once one masked Y is found

    # print("Intersecting axial slice numbers:", axial_slice_numbers)
    return axial_slice_numbers

def reversedNumber (total_length, sliceNumbers):
    # Original sublist
    sub_list = sliceNumbers # list(range(67, 96))  # [67, 68, ..., 95]

    # Compute reversed sublist by subtracting each value from (total_length - 1)
    reversed_sub_list = [total_length - 1 - x for x in sub_list]

    print("Original sublist:", sub_list)
    print("Reversed sublist:", reversed_sub_list)

    return reversed_sub_list

#Convert slices of Axis corresponding to Sagittal to png
def dicom_to_png(ds, output_path, default_center=None, default_width=None):
    # Step 1: Read and convert to HU using RescaleSlope and RescaleIntercept
    pixel_array = ds.pixel_array.astype(np.float32)
    slope = float(ds.get("RescaleSlope", 1))
    intercept = float(ds.get("RescaleIntercept", 0))
    hu = pixel_array * slope + intercept

    min_val = -100
    max_val = 200
    hu_clipped = np.clip(hu, min_val, max_val)

    # Step 4: Normalize to 0-255
    hu_norm = ((hu_clipped - min_val) / (max_val - min_val)) * 255.0
    hu_uint8 = np.clip(hu_norm, 0, 255).astype(np.uint8)

    # Step 5: Save image
    Image.fromarray(hu_uint8).save(output_path)
    print("imageShape:", hu_uint8.shape)
    print(f"Saved PNG: {output_path}")

def convert_selected_slices_by_z_index(dicom_folder, output_folder, mask_folder, overlay_folder, selected_z_indices,
                                       default_center=None, default_width=None):
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(mask_folder, exist_ok=True)
    os.makedirs(overlay_folder, exist_ok=True)

    # ✅ Step1: 读取所有 DICOM
    ds_list = []
    for f in os.listdir(dicom_folder):
        if f.startswith("._"):
            continue
        if not f.lower().endswith((".dcm", ".dcm.pk")):
            continue
        try:
            ds = pydicom.dcmread(os.path.join(dicom_folder, f))
            ds_list.append(ds)
        except:
            continue
    
    if not ds_list:
        print("[警告] 没有可用 DICOM")
        return

    # ✅ 排序
    ds_list.sort(key=lambda ds: float(ds.ImagePositionPatient[2])
                 if hasattr(ds, "ImagePositionPatient")
                 else float(ds.get("InstanceNumber", 0)))

    sel_set = set(selected_z_indices)
    print(f"[INFO] 选中 z 索引数量: {len(sel_set)}")

    # ✅ Step2: 遍历选中层
    for z_idx, ds in enumerate(ds_list):

        if z_idx not in sel_set:
            continue

        inst = ds.get("InstanceNumber", z_idx)
        try:
            inst_int = int(inst)
        except:
            inst_int = z_idx

        base = f"slice_{inst_int:03d}_0000"
        base_clean = base.replace("_0000", "")
        out_png = os.path.join(output_folder, base + ".png")
        dicom_to_png(ds, out_png, default_center, default_width)

        hu_img = ds.pixel_array.astype(np.float32)
        if "RescaleSlope" in ds and "RescaleIntercept" in ds:
            hu_img = hu_img * float(ds.RescaleSlope) + float(ds.RescaleIntercept)

        # SM_mask  = np.logical_and(hu_img >= 30, hu_img <= 34).astype(np.uint8)
        # VAT_mask = np.logical_and(hu_img >= -150, hu_img <= -50).astype(np.uint8)
        SAT_mask = np.logical_and(hu_img >= -190, hu_img <= -30).astype(np.uint8)
        
        # 加上骨头的HU范围
        # Bone_mask = np.logical_and(hu_img >= 150).astype(np.uint8)

        # 执行开运算（去除小白噪声）
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        SAT_mask_clean = cv2.morphologyEx(SAT_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)


        img = cv2.imread(out_png, 0)
        img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img_color[SAT_mask_clean == 1] = (0, 255, 255)    # 蓝

        cv2.imwrite(os.path.join(mask_folder, f"{base_clean}.png"), SAT_mask_clean * 255)
        cv2.imwrite(os.path.join(overlay_folder, f"{base_clean}_overlay.png"), img_color)

        print(f"[提取+分析] z={z_idx} -> {base}")

    print("✅ 选中层提取和 HU 分类全部完成！")
