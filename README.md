这个项目主要实现了医学影像（DICOM格式）处理和肌肉分割的自动化流程，核心流程如下：


1. **DICOM数据读取与预处理**  
   - 通过 SimpleITK 读取 DICOM 序列，获得三维体积数据和空间分辨率（spacing）。
   - 提取中间矢状面（sagittal）切片，并根据物理尺寸进行缩放和保存为新的 DICOM（`sagit_save.resize_and_save_sagittal_as_dicom`）。
   - 将 DICOM 切片转换为 PNG 格式（`sagit_save.dicom_to_balanced_png`）。

2. **L3脊柱分割**  
   - 使用 nnUNet 模型对中间矢状面 PNG 进行分割，得到 L3脊柱的 mask（`seg.run_nnunet_predict_and_overlay`）。
   - 对分割结果进行后处理（保留最大连通域），并生成 overlay 图像（`sagit_save.clean_mask_folder`, `sagit_save.overlay_and_save`）。

3. **横断面切片提取**  
   - 根据 L3 mask，确定与矢状面相交的所有轴向（axial）切片编号（`extract_slice.extract_axial_slices_from_sagittal_mask`）。
   - 将选中的 DICOM 切片转换为 PNG（`extract_slice.convert_selected_slices`）。

4. **肌肉分割**  
   - 对所有轴向 PNG 切片分别进行腰大肌和全肌肉分割（两次调用 `seg.run_nnunet_predict_and_overlay`）。
   - 对分割结果进行重命名，方便后续处理。

5. **统计与可视化**  
   - 对分割结果进行清洗、叠加可视化，并计算每张切片的 HU 值统计信息（`compute.process_all`）。
   - 结果保存为 overlay 图像和统计 CSV 文件。

## 主要调用逻辑

入口为 all_new.py 的 `main()` 函数，依次调用：
- sagit_save.py：DICOM切片处理、mask清洗与overlay生成
- extract_slice.py：mask加载、切片提取、DICOM转PNG
- seg.py：nnUNet模型推理
- compute.py：分割结果统计与可视化

## 运行需求

- Python 环境
- 依赖库：`SimpleITK`, `cv2`, `numpy`, `torch`, `pydicom`, `PIL`, `matplotlib`, `pandas`, `tqdm`
- nnUNet v2 代码与训练好的模型权重（放在 nnUNet_results 目录下）
- DICOM原始数据文件夹

## 运行方式

直接运行 all_new.py 即可自动完成全部流程：

```
python all_new.py
```

## 结果输出

- 分割后的 mask 和 overlay 图像
- 统计 CSV 文件（HU值、面积等）
- 主要输出目录见 all_new.py 变量定义部分

---




原来的 L3 做法

---

### 1. 打开测试图

- 先用 `SimpleITK` 读取 DICOM 序列，得到 3D 体数据（volume）：

```python
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)
reader.SetFileNames(dicom_names)
image = reader.Execute()
volume = sitk.GetArrayFromImage(image)  # [Z, Y, X]
```

- 取中间矢状面（侧视图）切片：

```python
x_mid = volume.shape[2] // 2
sagittal_slice = volume[:, :, x_mid]
```

---

### 2. 原来的方法识别完 L3 之后标注

- 先保存侧视图为 DICOM，再转为 PNG：

```python
dcm_path = resize_and_save_sagittal_as_dicom(sagittal_slice, spacing, dicom_names[len(dicom_names)//2])
png_path = dicom_to_balanced_png(dcm_path, L3_png_folder, scale_ratio)
```

- 用 nnUNet 模型推理，得到 L3 mask：

```python
run_nnunet_predict_and_overlay(L3_png_folder, L3_mask_folder, L3_model_dir, L3_checkpoint)
clean_mask_folder(L3_mask_folder, L3_cleaned_mask_folder)
overlay_and_save(L3_png_folder, L3_cleaned_mask_folder, L3_overlay_folder)
```

- 这一步会输出 L3 mask 和 overlay 图像（即在侧视图上标注出 L3 区域）。

---

### 3. 把信息传递给下一步

- 读取 L3 mask，恢复到原始分辨率：

```python
image_path = os.path.join(L3_cleaned_mask_folder, "sagittal_midResize.png")
mask = load_mask(image_path)
restored_mask = cv2.resize(mask, (orig_width, orig_height), interpolation=cv2.INTER_NEAREST)
```

- 用这个 mask 在 3D 体数据中定位 L3 区域，提取对应的横断面（axial slices）：

```python
axial_slices_numbers = extract_axial_slices_from_sagittal_mask(volume, restored_mask, x_mid, save_images=False)
selectedNumbers = reversedNumber(volume.shape[0], axial_slices_numbers)
convert_selected_slices(
    dicom_folder=dicom_folder,
    output_folder=slice_folder,
    selected_slices=selectedNumbers
)
```

- **传递的信息**：L3 区域的 mask（在侧视图上），以及对应的横断面序号，供后续肌肉分割等步骤使用。

---
