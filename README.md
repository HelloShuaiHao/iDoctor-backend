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

如需详细了解每一步的实现，可参考对应函数的源码链接：  
- `main`  
- `run_nnunet_predict_and_overlay`  
- `process_all`  
- `resize_and_save_sagittal_as_dicom`  
- `convert_selected_slices`