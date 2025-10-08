import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import os

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

    # Step 2: Get or define window center/width
    # wc_raw = ds.get("WindowCenter", np.mean(hu))
    # ww_raw = ds.get("WindowWidth", np.max(hu) - np.min(hu))

    # center = default_center or float(wc_raw[0] if isinstance(wc_raw, pydicom.multival.MultiValue) else wc_raw)
    # width = default_width or float(ww_raw[0] if isinstance(ww_raw, pydicom.multival.MultiValue) else ww_raw)

    # Step 3: Clip values to window range
    # min_val = center - width / 2
    # max_val = center + width / 2
    """
    2025/10/04
    使用 HU 值的 0 到 100 范围进行线性归一
    """
    min_val = -150
    max_val = 200
    hu_clipped = np.clip(hu, min_val, max_val)

    # Step 4: Normalize to 0-255
    hu_norm = ((hu_clipped - min_val) / (max_val - min_val)) * 255.0
    hu_uint8 = np.clip(hu_norm, 0, 255).astype(np.uint8)

    # Step 5: Save image
    Image.fromarray(hu_uint8).save(output_path)
    print("imageShape:", hu_uint8.shape)
    print(f"Saved PNG: {output_path}")


def convert_selected_slices(dicom_folder, output_folder, selected_slices):
    os.makedirs(output_folder, exist_ok=True)

    for filename in sorted(os.listdir(dicom_folder)):
        if filename.startswith("._"):
            continue

        if not filename.lower().endswith((".dcm", ".dcm.pk")):
            continue

        dicom_path = os.path.join(dicom_folder, filename)
        try:
            ds = pydicom.dcmread(dicom_path)
            instance_number = int(ds.get("InstanceNumber", -1))

            if instance_number in selected_slices:
                output_filename = f"slice_{instance_number:03d}_0000.png"
                output_path = os.path.join(output_folder, output_filename)
                dicom_to_png(ds, output_path)

        except Exception as e:
            print(f"Error processing {filename}: {e}")


def convert_selected_slices_by_z_index(dicom_folder, output_folder, selected_z_indices,
                                       default_center=None, default_width=None):
    """
    根据构建 volume 时的物理顺序 (ImagePositionPatient[2] -> 排序) 用 z 索引导出对应切片。
    selected_z_indices: 直接来自 extract_axial_slices_from_sagittal_mask 返回的 z list
    """
    os.makedirs(output_folder, exist_ok=True)
    # 读取并收集
    ds_list = []
    for f in os.listdir(dicom_folder):
        if f.startswith("._"):
            continue
        if not f.lower().endswith((".dcm", ".dcm.pk")):
            continue
        path = os.path.join(dicom_folder, f)
        try:
            ds = pydicom.dcmread(path)
            ds_list.append(ds)
        except Exception as e:
            print(f"[跳过] 读取失败 {f}: {e}")
    if not ds_list:
        print("[警告] 没有可用 DICOM")
        return

    # 排序（与 SimpleITK 读取顺序对齐）
    def z_key(ds):
        try:
            return float(ds.ImagePositionPatient[2])
        except Exception:
            return float(ds.get("InstanceNumber", 0))
    ds_list.sort(key=z_key)

    sel_set = set(selected_z_indices)
    print(f"[INFO] 选中 z 索引数量: {len(sel_set)}  原始列表长度: {len(selected_z_indices)}")

    for z_idx, ds in enumerate(ds_list):
        if z_idx in sel_set:
            inst = ds.get("InstanceNumber", z_idx)
            try:
                inst_int = int(inst)
            except:
                inst_int = z_idx
            out_name = f"slice_{inst_int:03d}_0000.png"
            out_path = os.path.join(output_folder, out_name)
            dicom_to_png(ds, out_path, default_center=default_center, default_width=default_width)
            # 调试输出
            ipp = getattr(ds, "ImagePositionPatient", ["?", "?", "?"])
            print(f"[导出] z_idx={z_idx} -> {out_name}  InstanceNumber={inst}  Z={ipp[2] if len(ipp)>=3 else '?'}")            


