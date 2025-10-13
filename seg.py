import os
import torch
import gc
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

def run_nnunet_predict_and_overlay(input_dir: str, output_dir: str, model_dir: str, checkpoint: str = "checkpoint_final.pth"):
    for k in ['nnUNet_raw', 'nnUNet_preprocessed', 'nnUNet_results']:
        if k not in os.environ:
            os.environ[k] = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)

    # 推理前清理显存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        allocated = torch.cuda.memory_allocated() / 1024**3
        print(f"[GPU] 推理前显存: {allocated:.2f} GB")

    # 单线程模式
    old_num_threads = os.environ.get('OMP_NUM_THREADS')
    os.environ['OMP_NUM_THREADS'] = '1'

    predictor = None
    try:
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

        print(f"[DEBUG] 开始推理: {input_dir} -> {output_dir}")
        
        predictor.predict_from_files(
            input_dir, 
            output_dir,
            save_probabilities=False,
            num_processes_preprocessing=1,
            num_processes_segmentation_export=1,
        )

        print(f"[DEBUG] 推理完成: {output_dir}")

    finally:
        # 强制释放资源
        if predictor is not None:
            del predictor
        
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            allocated = torch.cuda.memory_allocated() / 1024**3
            print(f"[GPU] 推理后显存: {allocated:.2f} GB")
        
        # 恢复环境变量
        if old_num_threads:
            os.environ['OMP_NUM_THREADS'] = old_num_threads
        else:
            os.environ.pop('OMP_NUM_THREADS', None)