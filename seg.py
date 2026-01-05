import os
import glob
import cv2
import torch
import numpy as np
import imageio.v2 as imageio
import multiprocessing as mp
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

def run_nnunet_predict_and_overlay(input_dir: str, output_dir: str, model_dir: str, checkpoint: str = "checkpoint_final.pth"):
    for k in ['nnUNet_raw', 'nnUNet_preprocessed', 'nnUNet_results']:
        os.environ[k] = os.environ.get(k, f"./{k}")
        os.makedirs(os.environ[k], exist_ok=True)

    os.makedirs(output_dir, exist_ok=True)

    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=True,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        verbose=True,
        verbose_preprocessing=True,
    )
    predictor.initialize_from_trained_model_folder(
        model_dir,
        use_folds="all",
        checkpoint_name=checkpoint,
    )

    # —— 目录模式！——
    predictor.predict_from_files(
        input_dir, 
        output_dir,
        save_probabilities=False,
        num_processes_preprocessing=1,
    )

    print("🎯 Segmentation done.")

# def clean_psoas_mask(mask_bin):
#     """
#     输入: 0/1 mask (np.uint8)
#     输出: 0/1 mask
#     """
#     # 转为 255-based mask for connected-component correctness
#     mask_uint8 = (mask_bin * 255).astype(np.uint8)

#     # Step0: 连通域
#     num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_uint8, connectivity=8)
#     if num_labels <= 2:
#         return mask_bin.copy()

#     # Step1: 面积过滤
#     areas = stats[1:, 4]
#     median_area = np.median(areas)
#     area_threshold = median_area * 0.7

#     area_filtered = np.zeros_like(mask_uint8)
#     valid = []
#     for i in range(1, num_labels):
#         if stats[i, 4] >= area_threshold:
#             area_filtered[labels == i] = 255
#             valid.append(i)

#     # 如果过滤后 <=2 块 → 已确定目标
#     if len(valid) <= 2:
#         return (area_filtered > 0).astype(np.uint8)

#     # Step2: 重新连通域 + 左右分类
#     num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(area_filtered, connectivity=8)
#     ys, xs = np.where(area_filtered > 0)
#     if len(xs) == 0:
#         return mask_bin.copy()

#     center_x = (xs.min() + xs.max()) / 2.0

#     left_list, right_list = [], []
#     for i in range(1, num_labels):
#         cx, cy = centroids[i]
#         area = stats[i, 4]
#         if cx < center_x:
#             left_list.append((i, cy, area))
#         else:
#             right_list.append((i, cy, area))

#     if len(left_list) == 0 or len(right_list) == 0:
#         keep = sorted(range(1, num_labels), key=lambda i: stats[i,4], reverse=True)[:2]
#         result = np.zeros_like(mask_uint8)
#         for lab in keep:
#             result[labels == lab] = 255
#         return (result > 0).astype(np.uint8)

#     # Step3: 穷举组合 → Y差最小最佳组合
#     best_pair = None
#     min_diff = float('inf')
#     for L in left_list:
#         for R in right_list:
#             diff = abs(L[1] - R[1])
#             if diff < min_diff:
#                 min_diff = diff
#                 best_pair = (L[0], R[0])

#     result = np.zeros_like(mask_uint8)
#     for lab in best_pair:
#         result[labels == lab] = 255

#     return (result > 0).astype(np.uint8)


# def process_psoas_folder(input_folder, output_folder):
#     os.makedirs(output_folder, exist_ok=True)
    
#     for fname in os.listdir(input_folder):
#         if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
#             continue

#         in_path = os.path.join(input_folder, fname)
#         out_path = os.path.join(output_folder, fname)

#         mask = cv2.imread(in_path, cv2.IMREAD_GRAYSCALE)
#         if mask is None:
#             print(f"❌ 跳过：无法读取 {fname}")
#             continue

#         mask_bin = (mask > 0).astype(np.uint8)
#         result_bin = clean_psoas_mask(mask_bin)

#         cv2.imwrite(out_path, result_bin)
#         print(f"✅ 处理完成: {fname}")

#     print("\n🎯 全部mask后处理完成 ✅")



# # ✅ 使用示例
# process_psoas_folder("D:/Med/yao", "D:/Med/yao/filterednewnew")