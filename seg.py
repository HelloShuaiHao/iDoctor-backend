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
    print(f"[DEBUG] 开始推理: {input_dir} -> {output_dir}")
    
    predictor.predict_from_files(
        input_dir, 
        output_dir,
        save_probabilities=False,
        num_processes_preprocessing=0,  # ✅ 禁用多进程，避免死锁
        num_processes_segmentation_export=0,  # ✅ 禁用导出多进程
    )

    print(f"[DEBUG] 推理完成: {output_dir}")
    print("🎯 Segmentation done.")

# # 用法示例
# if __name__ == "__main__":
#     try:
#         mp.set_start_method("spawn", force=True)
#     except RuntimeError:
#         pass

#     run_nnunet_predict_and_overlay(
#         input_dir="Axisal_1504425",
#         output_dir="conall2_predictions",
#         model_dir="nnUNet_results/Dataset001_MyPNGTask/nnUNetTrainer__nnUNetPlans__2d",
#         checkpoint_name="checkpoint_final.pth"
#     )
