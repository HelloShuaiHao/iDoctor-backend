import os, time, glob, hashlib, threading, traceback, cv2, torch, gc
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
from pipeline_logging import write_log

def _file_md5(path):
    try:
        with open(path, "rb") as f:
            import hashlib as _h
            return _h.md5(f.read()).hexdigest()[:8]
    except Exception:
        return "NA"

def run_nnunet_predict_and_overlay(input_dir: str,
                                   output_dir: str,
                                   model_dir: str,
                                   checkpoint: str = "checkpoint_final.pth"):
    """增加详细日志和进度 watchdog"""
    for k in ['nnUNet_raw', 'nnUNet_preprocessed', 'nnUNet_results']:
        if k not in os.environ:
            os.environ[k] = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)
    log_root = os.path.dirname(output_dir) if os.path.dirname(output_dir) else output_dir
    this_file = os.path.abspath(__file__)
    write_log(log_root, f"[nnUNet] START model_dir={model_dir} checkpoint={checkpoint} input_dir={input_dir} output_dir={output_dir}")
    write_log(log_root, f"[nnUNet] seg_py={this_file} md5={_file_md5(this_file)}")

    # 模型目录快照
    if not os.path.isdir(model_dir):
        write_log(log_root, f"[nnUNet] MODEL_DIR_MISSING {model_dir}")
    else:
        items = sorted(os.listdir(model_dir))
        write_log(log_root, f"[nnUNet] model_dir_items_count={len(items)} sample={items[:10]}")
        for nf in [checkpoint, 'plans.json']:
            if not any(nf in x for x in items):
                write_log(log_root, f"[nnUNet] WARN missing_like={nf}")

    # 输入统计
    all_png = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
    png_0000 = [f for f in all_png if f.endswith('_0000.png')]
    write_log(log_root, f"[nnUNet] input_stats total_png={len(all_png)} total_0000={len(png_0000)} sample={all_png[:10]}")
    for f in png_0000[:3]:
        p = os.path.join(input_dir, f)
        try:
            img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if img is None:
                write_log(log_root, f"[nnUNet] IMG_FAIL {f}")
            else:
                write_log(log_root, f"[nnUNet] IMG {f} shape={img.shape} dtype={img.dtype}")
        except Exception as ie:
            write_log(log_root, f"[nnUNet] IMG_ERR {f} {ie}")

    # GPU 前显存
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache(); torch.cuda.synchronize()
            write_log(log_root, f"[nnUNet] GPU_BEFORE {torch.cuda.memory_allocated()/1024**3:.2f}GB")
        except Exception as ge:
            write_log(log_root, f"[nnUNet] GPU_BEFORE_ERR {ge}")

    old_num_threads = os.environ.get('OMP_NUM_THREADS')
    os.environ['OMP_NUM_THREADS'] = '1'

    predictor = None
    start_time = time.time()
    done_flag = {"v": False}
    timeout_seconds = 180

    def watchdog():
        last_report = -1
        while not done_flag["v"]:
            elapsed = time.time() - start_time
            nii_count = len(glob.glob(os.path.join(output_dir, '*.nii.gz')))
            if nii_count != last_report or int(elapsed) % 30 == 0:
                gpu_mem = 0.0
                if torch.cuda.is_available():
                    try:
                        gpu_mem = torch.cuda.memory_allocated()/1024**3
                    except Exception:
                        pass
                write_log(log_root, f"[nnUNet] PROGRESS elapsed={elapsed:.1f}s nii={nii_count} gpu_mem={gpu_mem:.2f}GB")
                last_report = nii_count
            if elapsed > timeout_seconds and not done_flag['v']:
                write_log(log_root, f"[nnUNet] WATCHDOG_TIMEOUT elapsed={elapsed:.1f}s (>={timeout_seconds}s)")
            time.sleep(5)

    wd = threading.Thread(target=watchdog, daemon=True)
    wd.start()

    try:
        predictor = nnUNetPredictor(
            tile_step_size=0.5,
            use_gaussian=True,
            use_mirroring=True,
            perform_everything_on_device=True,
            device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
            verbose=True,
            verbose_preprocessing=True,
        )
        write_log(log_root, "[nnUNet] predictor_created")
        predictor.initialize_from_trained_model_folder(
            model_dir,
            # use_folds='all',
            use_folds=None,  # 设为 None 让它直接在根目录找权重
            checkpoint_name=checkpoint,
        )
        write_log(log_root, "[nnUNet] model_initialized begin_predict")
        write_log(log_root, f"[nnUNet] PREDICT_CALL input_type={type(input_dir)} is_dir={os.path.isdir(input_dir)}")
        # 确保权重存在, 若根目录没有则尝试从 fold_all 软链接常见文件名
        weight_root = os.path.join(model_dir, checkpoint)
        
        # 删除原来的软链接逻辑
        # 直接验证权重是否存在
        weight_path = os.path.join(model_dir, checkpoint)
        if not os.path.isfile(weight_path):
            raise RuntimeError(f"权重文件不存在: {weight_path}")
        write_log(log_root, f"[nnUNet] checkpoint_found={weight_path}")

        # 2. 构造 list-of-lists cases (单模态) 而不是传目录字符串
        cases = [[os.path.join(input_dir, f)] for f in sorted(os.listdir(input_dir)) if f.endswith('_0000.png')]
        write_log(log_root, f"[nnUNet] CASES_BUILT count={len(cases)} first={[os.path.basename(c[0]) for c in cases[:5]]}")
        if not cases:
            raise RuntimeError("未找到 *_0000.png 作为 nnUNet 输入")

        # 3. 推理  
        infer_t0 = time.time()
        predictor.predict_from_files(
            cases,
            output_dir,
            save_probabilities=False,
            num_processes_preprocessing=1,
            num_processes_segmentation_export=0,
        )
        infer_t1 = time.time()

        # 4. 等待最多 60s 收集 nii (通常即刻出现)
        deadline = time.time() + 60
        nii_files = []
        while time.time() < deadline:
            nii_files = [f for f in os.listdir(output_dir) if f.endswith('.nii.gz')]
            if len(nii_files) >= len(cases):
                break
            time.sleep(1)
        dur = time.time() - start_time
        out_files = sorted(os.listdir(output_dir))
        write_log(log_root, f"[nnUNet] DONE duration={dur:.2f}s infer_time={infer_t1-infer_t0:.2f}s out_total={len(out_files)} nii={len(nii_files)} sample={out_files[:12]}")
        if len(nii_files) == 0:
            raise RuntimeError("推理完成但未生成 *.nii.gz (检查权重/输入尺寸/模型配置)")
    except Exception as e:
        write_log(log_root, f"[nnUNet] EXCEPTION {e}")
        traceback.print_exc()
    finally:
        done_flag['v'] = True
        wd.join(timeout=1)
        if predictor is not None:
            del predictor
        gc.collect()
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache(); torch.cuda.synchronize()
                write_log(log_root, f"[nnUNet] GPU_AFTER {torch.cuda.memory_allocated()/1024**3:.2f}GB")
            except Exception as ge2:
                write_log(log_root, f"[nnUNet] GPU_AFTER_ERR {ge2}")
        if old_num_threads:
            os.environ['OMP_NUM_THREADS'] = old_num_threads
        else:
            os.environ.pop('OMP_NUM_THREADS', None)
        write_log(log_root, f"[nnUNet] END total_elapsed={time.time()-start_time:.2f}s")