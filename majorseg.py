import os
import cv2
import numpy as np
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2 import model_zoo

def build_predictor(model_path, score_thresh=0.3):
    cfg = get_cfg()
    cfg.merge_from_file(
        model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thresh
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    return DefaultPredictor(cfg)


def extract_masks(instances):
    masks = []
    if len(instances) == 0:
        return masks
    pred_masks = instances.pred_masks.cpu().numpy()
    for m in pred_masks:
        masks.append(m.astype(np.uint8))  # 0/1
    return masks


def select_psoas_masks(bone_mask, psoas_masks):
    if not psoas_masks:
        return None, None

    ys_bone, xs_bone = np.where(bone_mask > 0)
    if len(xs_bone) == 0:
        return None, None

    bone_cx = xs_bone.mean()
    bone_cy = ys_bone.mean()

    dist_map = cv2.distanceTransform(
        (1 - bone_mask).astype(np.uint8),
        cv2.DIST_L2,
        5
    )

    left_candidates = []    # (min_dist, mask)
    right_candidates = []   # (min_dist, mask)

    delta = 2
    overlap_thresh = 0.8

    for m in psoas_masks:
        ys_m, xs_m = np.where(m > 0)

        # R1: 空 mask
        if len(xs_m) == 0:
            continue

        # R0: 与 bone 重合比例
        overlap_pixels = np.sum((m > 0) & (bone_mask > 0))
        overlap_ratio = overlap_pixels / (len(xs_m) + 1e-6)
        if overlap_ratio >= overlap_thresh:
            continue

        # R2: y 方向与 bone_cy ± 2 无交集
        if ys_m.max() < bone_cy - delta or ys_m.min() > bone_cy + delta:
            continue

        # R3: 左右判断
        cx = xs_m.mean()

        # R4: 最近距离
        min_dist = dist_map[m > 0].min()

        if cx < bone_cx:
            left_candidates.append((min_dist, m))
        else:
            right_candidates.append((min_dist, m))

    left_mask = None
    right_mask = None

    if left_candidates:
        left_candidates.sort(key=lambda x: x[0])
        left_mask = left_candidates[0][1]

    if right_candidates:
        right_candidates.sort(key=lambda x: x[0])
        right_mask = right_candidates[0][1]

    return left_mask, right_mask


def check_error_conditions(bone_mask, left_mask, right_mask, min_sym=0.25, max_sym=4.0):

    if left_mask is None or right_mask is None:
        print("❌ Error: Only one psoas detected.")
        return True

    area_L = np.sum(left_mask > 0)
    area_R = np.sum(right_mask > 0)

    if area_L == 0 or area_R == 0:
        print("❌ Error: One side area zero.")
        return True

    ratio = area_L / area_R
    if ratio < min_sym or ratio > max_sym:
        print(f"❌ Error: Left/Right area ratio abnormal: {ratio:.2f}")
        return True

    ys, xs = np.where(bone_mask > 0)
    x_min, x_max = xs.min(), xs.max()
    bone_center_x = (x_min + x_max) / 2

    Ly, Lx = np.mean(np.where(left_mask > 0), axis=1)
    Ry, Rx = np.mean(np.where(right_mask > 0), axis=1)
    
    if not (Lx < bone_center_x and Rx > bone_center_x):
        print("❌ Error: Not symmetric around bone center.")
        return True

    return False


def process_single_image(
    img_path,
    bone_predictor,
    psoas_predictor,
    save_dir
):
    img = cv2.imread(img_path)
    if img is None:
        print(f"Cannot read: {img_path}")
        return

    H, W = img.shape[:2]

    # -------- 文件名处理 --------
    orig_name = os.path.basename(img_path)
    base, _ = os.path.splitext(orig_name)
    if base.endswith("_0000"):
        base = base[:-5]

    os.makedirs(save_dir, exist_ok=True)

    # ===============================
    # 1. 骨头检测
    # ===============================
    bone_out = bone_predictor(img)["instances"].to("cpu")
    bone_masks = extract_masks(bone_out)

    if len(bone_masks) == 0:
        print(f"No bone detected: {img_path}")
        return

    bone_mask = bone_masks[np.argmax([m.sum() for m in bone_masks])].astype(np.uint8)

    # ===============================
    # 2. 腰大肌检测
    # ===============================
    psoas_out = psoas_predictor(img)["instances"].to("cpu")
    psoas_masks = extract_masks(psoas_out)

    if len(psoas_masks) == 0:
        print(f"No psoas detected: {img_path}")
        return

    # ===============================
    # 3. 左右最近腰大肌筛选
    # ===============================
    left_mask, right_mask = select_psoas_masks(
        bone_mask,
        psoas_masks
    )

    if left_mask is None or right_mask is None:
        print(f"❌ Skip: missing left or right psoas → {img_path}")
        return

    # ===============================
    # 4. 合成并保存 final psoas mask
    # ===============================
    final_psoas_mask = np.zeros((H, W), dtype=np.uint8)
    final_psoas_mask[left_mask > 0] = 1
    final_psoas_mask[right_mask > 0] = 1

    out_path = os.path.join(save_dir, base + ".png")
    cv2.imwrite(out_path, final_psoas_mask * 255)

    print(f"✔ Saved final psoas mask: {out_path}")



def run_psoas_pipeline(input_dir, output_dir, bone_model_path, psoas_model_path):
    os.makedirs(output_dir, exist_ok=True)

    bone_predictor  = build_predictor(bone_model_path,  score_thresh=0.5)
    psoas_predictor = build_predictor(psoas_model_path, score_thresh=0.3)

    for fname in sorted(os.listdir(input_dir)):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            process_single_image(
                os.path.join(input_dir, fname),
                bone_predictor,
                psoas_predictor,
                output_dir
            )

    print(f"\n🎉 ALL DONE! 输出保存在：{output_dir}")
