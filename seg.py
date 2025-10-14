import os
import torch
import gc
import time
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
from pipeline_logging import write_log

def run_nnunet_predict_and_overlay(input_dir: str, output_dir: str, model_dir: str, checkpoint: str = "checkpoint_final.pth"):
    for k in ['nnUNet_raw', 'nnUNet_preprocessed', 'nnUNet_results']:
        if k not in os.environ:
            os.environ[k] = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)
    log_root = os.path.dirname(output_dir) if os.path.dirname(output_dir) else output_dir
    write_log(log_root, f"[nnUNet] START model_dir={model_dir} checkpoint={checkpoint} input_dir={input_dir} output_dir={output_dir}")

    # 推理前清理显存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        allocated = torch.cuda.memory_allocated() / 1024**3
        write_log(log_root, f"[GPU] before={allocated:.2f}GB")

    # 单线程模式
    old_num_threads = os.environ.get('OMP_NUM_THREADS')
    os.environ['OMP_NUM_THREADS'] = '1'

    predictor = None
    start_time = time.time()
    input_files = [f for f in os.listdir(input_dir) if f.endswith('_0000.png') or f.endswith('.png')]
    write_log(log_root, f"[nnUNet] input_files_count={len(input_files)} sample={input_files[:5]}")
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

        write_log(log_root, f"[nnUNet] initialized folds=all begin_infer")
        
        predictor.predict_from_files(
            input_dir, 
            output_dir,
            save_probabilities=False,
            num_processes_preprocessing=1,
            num_processes_segmentation_export=1,
        )
        dur = time.time() - start_time
        out_files = os.listdir(output_dir)
        write_log(log_root, f"[nnUNet] DONE duration={dur:.2f}s outputs={len(out_files)} sample={out_files[:5]}")

    finally:
        # 强制释放资源
        if predictor is not None:
            del predictor
        
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            allocated = torch.cuda.memory_allocated() / 1024**3
            write_log(log_root, f"[GPU] after={allocated:.2f}GB")
        
        # 恢复环境变量
        if old_num_threads:
            os.environ['OMP_NUM_THREADS'] = old_num_threads
        else:
            os.environ.pop('OMP_NUM_THREADS', None)
        write_log(log_root, "[nnUNet] resources released")