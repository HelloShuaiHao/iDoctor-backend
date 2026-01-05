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


def select_psoas_masks(bone_mask, psoas_masks, debug_prefix=""):
    """
    规则（按顺序）：
    R0. 若 psoas mask 与 bone mask 重合比例 ≥ 50% → 直接删除
        overlap_ratio = |m ∩ bone| / |m|
    R1. 空 mask 删除
    R2. mask 的 y-range 必须与 [bone_cy-2, bone_cy+2] 有交集
    R3. 左右由 x 方向相对 bone_cx 决定
    R4. 每侧选：到 bone 的最近距离 min_dist 最小的一个（dist_map[m>0].min）

    debug_prefix: 可传入 slice 名，便于日志定位
    """
    if not psoas_masks:
        print(f"[{debug_prefix}] ❌ No psoas masks at all")
        return None, None

    ys_bone, xs_bone = np.where(bone_mask > 0)
    if len(xs_bone) == 0:
        print(f"[{debug_prefix}] ❌ Bone mask empty")
        return None, None

    bone_cx = xs_bone.mean()
    bone_cy = ys_bone.mean()

    # distance transform: 每个像素到最近骨头像素的欧氏距离（像素单位）
    dist_map = cv2.distanceTransform(
        (1 - bone_mask).astype(np.uint8),
        cv2.DIST_L2,
        5
    )

    left_candidates = []   # (min_dist, idx, mask)
    right_candidates = []  # (min_dist, idx, mask)

    delta = 2
    overlap_thresh = 0.8

    for idx, m in enumerate(psoas_masks):
        ys_m, xs_m = np.where(m > 0)

        # ---------- R1：空 mask ----------
        if len(xs_m) == 0:
            # print(f"[{debug_prefix}] ❌ Mask {idx}: empty mask → removed (R1)")
            continue

        # ---------- R0：与 bone 重合比例 ----------
        overlap_pixels = np.sum((m > 0) & (bone_mask > 0))
        overlap_ratio = overlap_pixels / (len(xs_m) + 1e-6)
        if overlap_ratio >= overlap_thresh:
            print(
                f"[{debug_prefix}] ❌ Mask {idx}: overlap with bone = "
                f"{overlap_ratio:.2f} ≥ {overlap_thresh} → removed (R0)"
            )
            continue

        # ---------- R2：与 bone_cy ± 2 无交集 ----------
        if ys_m.max() < bone_cy - delta or ys_m.min() > bone_cy + delta:
            print(
                f"[{debug_prefix}] ❌ Mask {idx}: "
                f"y-range [{ys_m.min()}–{ys_m.max()}] does NOT intersect "
                f"[{bone_cy - delta:.1f}–{bone_cy + delta:.1f}] (bone_cy±{delta}) "
                f"→ removed (R2)"
            )
            continue

        # ---------- R3：左右判断 ----------
        cx = xs_m.mean()
        side = "L" if cx < bone_cx else "R"

        # ---------- R4：min_dist（你指定的方式） ----------
        min_dist = dist_map[m > 0].min()

        print(
            f"[{debug_prefix}] ✔ Mask {idx}: kept as candidate | "
            f"side={side}, min_dist={min_dist:.2f}, overlap={overlap_ratio:.2f}"
        )

        if cx < bone_cx:
            left_candidates.append((min_dist, idx, m))
        else:
            right_candidates.append((min_dist, idx, m))

    # ===============================
    # 左侧选择：min_dist 最小
    # ===============================
    left_mask = None
    if left_candidates:
        left_candidates.sort(key=lambda x: x[0])
        best_min_dist, best_idx, best_mask = left_candidates[0]
        left_mask = best_mask
        print(f"[{debug_prefix}] ⭐ Left selected: Mask {best_idx} (min_dist={best_min_dist:.2f})")

        for md, idx, _ in left_candidates[1:]:
            print(
                f"[{debug_prefix}] ❌ Mask {idx}: left side but min_dist={md:.2f} "
                f"> best → removed (R4)"
            )
    else:
        print(f"[{debug_prefix}] ❌ No valid LEFT psoas")

    # ===============================
    # 右侧选择：min_dist 最小
    # ===============================
    right_mask = None
    if right_candidates:
        right_candidates.sort(key=lambda x: x[0])
        best_min_dist, best_idx, best_mask = right_candidates[0]
        right_mask = best_mask
        print(f"[{debug_prefix}] ⭐ Right selected: Mask {best_idx} (min_dist={best_min_dist:.2f})")

        for md, idx, _ in right_candidates[1:]:
            print(
                f"[{debug_prefix}] ❌ Mask {idx}: right side but min_dist={md:.2f} "
                f"> best → removed (R4)"
            )
    else:
        print(f"[{debug_prefix}] ❌ No valid RIGHT psoas")

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


# def process_single_image(
#     img_path,
#     bone_predictor,
#     psoas_predictor,
#     save_dir
# ):
#     img = cv2.imread(img_path)
#     if img is None:
#         print(f"Cannot read: {img_path}")
#         return

#     H, W = img.shape[:2]

#     # -------- 文件名处理 --------
#     orig_name = os.path.basename(img_path)
#     base, _ = os.path.splitext(orig_name)
#     if base.endswith("_0000"):
#         base = base[:-5]

#     os.makedirs(save_dir, exist_ok=True)

#     # ===============================
#     # 1. 骨头检测
#     # ===============================
#     bone_out = bone_predictor(img)["instances"].to("cpu")
#     bone_masks = extract_masks(bone_out)

#     if len(bone_masks) == 0:
#         print(f"No bone detected: {img_path}")
#         return

#     bone_mask = bone_masks[np.argmax([m.sum() for m in bone_masks])].astype(np.uint8)

#     # ===============================
#     # 2. 腰大肌检测（predictor 原始输出）
#     # ===============================
#     psoas_out = psoas_predictor(img)["instances"].to("cpu")
#     psoas_masks = extract_masks(psoas_out)

#     if len(psoas_masks) == 0:
#         print(f"No psoas detected: {img_path}")
#         return

#     # =====================================================
#     # 2.5 🔴 DEBUG：保存“原始 psoas 检测 mask”
#     # =====================================================

#     # 2.5.1 合并所有 psoas mask（二值）
#     raw_psoas_mask = np.zeros((H, W), dtype=np.uint8)
#     for m in psoas_masks:
#         raw_psoas_mask[m > 0] = 1

#     raw_mask_path = os.path.join(save_dir, base + "_psoas_raw_mask.png")
#     cv2.imwrite(raw_mask_path, raw_psoas_mask * 255)

#     # 2.5.2 overlay 到原图（推荐）
#     overlay = img.copy()
#     if overlay.ndim == 2:
#         overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

#     psoas_color = np.zeros_like(overlay)
#     psoas_color[raw_psoas_mask > 0] = (255, 0, 0)  # 蓝色表示 psoas（BGR）

#     alpha = 0.4
#     overlay = cv2.addWeighted(overlay, 1.0, psoas_color, alpha, 0)

#     raw_overlay_path = os.path.join(save_dir, base + "_psoas_raw_overlay.png")
#     cv2.imwrite(raw_overlay_path, overlay)

#     print(f"🟦 Saved raw psoas mask: {raw_mask_path}")
#     print(f"🟦 Saved raw psoas overlay: {raw_overlay_path}")

#     # ===============================
#     # 3. 左右最近腰大肌筛选（你的主逻辑）
#     # ===============================
#     left_mask, right_mask = select_psoas_masks(
#         bone_mask,
#         psoas_masks
#     )

#     if left_mask is None or right_mask is None:
#         print(f"❌ Skip: missing left or right psoas → {img_path}")
#         return

#     # ===============================
#     # 4. 合成 final psoas mask
#     # ===============================
#     final_psoas_mask = np.zeros((H, W), dtype=np.uint8)
#     final_psoas_mask[left_mask > 0] = 1
#     final_psoas_mask[right_mask > 0] = 1

#     final_path = os.path.join(save_dir, base + "_psoas_final.png")
#     cv2.imwrite(final_path, final_psoas_mask * 255)

#     print(f"✔ Saved final psoas mask: {final_path}")

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
        psoas_masks,
        debug_prefix=base
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

# import os
# import cv2
# import numpy as np


# # ============================================================
# # 1) 选出最近两个 + 所有紧贴骨头的 mask
# # ============================================================
# def select_psoas_masks(bone_mask, psoas_masks, close_thresh=10):
#     if not psoas_masks:
#         return None, None
#     ys, xs = np.where(bone_mask > 0)
#     if len(ys) == 0:
#         return None, None

#     bone_top_y = ys.min()

#     H, W = bone_mask.shape
#     valid_masks = []
#     for m in psoas_masks:
#         coords = np.where(m > 0)
#         if len(coords[0]) == 0:
#             continue

#         cy, cx = np.mean(coords, axis=1)
#         cy = int(round(cy))
#         cx = int(round(cx))
#         if not (0 <= cy < H and 0 <= cx < W):
#             continue
#         if cy < bone_top_y:
#             continue
#         if bone_mask[cy, cx] > 0:
#             continue

#         valid_masks.append(m)

#     if len(valid_masks) == 0:
#         return None, None

#     if len(valid_masks) == 1:
#         return valid_masks[0], None

#     # Step 2: 距离 transform
#     dist_map = cv2.distanceTransform((1 - bone_mask).astype(np.uint8),
#                                      cv2.DIST_L2, 5)

#     # Step 3: 找两个最近的
#     scores = []
#     for m in valid_masks:
#         mean_dist = dist_map[m > 0].mean()
#         scores.append((mean_dist, m))
#     scores.sort(key=lambda x: x[0])

#     best_masks = [scores[0][1]]
#     if len(scores) > 1:
#         best_masks.append(scores[1][1])

#     # Step 4: 找所有紧贴骨头的 mask（最小距离 <= close_thresh）
#     close_masks = []
#     for m in valid_masks:
#         if dist_map[m > 0].min() <= close_thresh:
#             close_masks.append(m)

#     return best_masks, close_masks


# # ============================================================
# # 2) 多 mask 左右分组 + 每侧选面积最大的作为主 psoas
# # ============================================================
# def assign_left_right_multi(bone_mask, masks):
#     if not masks:
#         return None, None, [], []

#     ys, xs = np.where(bone_mask > 0)
#     bone_center_x = (xs.min() + xs.max()) / 2

#     left_group = []
#     right_group = []

#     # 分组
#     for m in masks:
#         ys_m, xs_m = np.where(m > 0)
#         cy, cx = np.mean(ys_m), np.mean(xs_m)
#         if cx < bone_center_x:
#             left_group.append(m)
#         else:
#             right_group.append(m)

#     # 每组选面积最大的作为 main
#     def pick_main(group):
#         if not group:
#             return None
#         arr = [(np.sum(g > 0), g) for g in group]
#         arr.sort(key=lambda x: -x[0])
#         return arr[0][1]

#     left_main = pick_main(left_group)
#     right_main = pick_main(right_group)

#     return left_main, right_main, left_group, right_group


# # ============================================================
# # 3) 主 psoas 的错误检查（最稳定）
# # ============================================================
# def check_error_conditions_multi(bone_mask, left_main, right_main,
#                                  min_sym=0.25, max_sym=4.0):

#     if left_main is None or right_main is None:
#         print("❌ Error: Missing left or right psoas.")
#         return True

#     area_L = np.sum(left_main > 0)
#     area_R = np.sum(right_main > 0)
#     if area_L == 0 or area_R == 0:
#         print("❌ Error: One side area zero.")
#         return True

#     ratio = area_L / area_R
#     if not (min_sym <= ratio <= max_sym):
#         print(f"❌ Error: area ratio abnormal: {ratio:.2f}")
#         return True

#     ys, xs = np.where(bone_mask > 0)
#     bone_center_x = (xs.min() + xs.max()) / 2

#     Ly, Lx = np.mean(np.where(left_main > 0), axis=1)
#     Ry, Rx = np.mean(np.where(right_main > 0), axis=1)

#     if not (Lx < bone_center_x and Rx > bone_center_x):
#         print("❌ Error: Not symmetric around bone.")
#         return True

#     return False


# # ============================================================
# # 4) 单张图片处理（最终输出所有有效 psoas mask）
# # ============================================================
# def process_single_image(img_path, bone_predictor, psoas_predictor, save_dir):

#     img = cv2.imread(img_path)
#     if img is None:
#         print(f"Cannot read: {img_path}")
#         return

#     H, W = img.shape[:2]

#     # 统一文件名
#     fname = os.path.basename(img_path)
#     base, ext = os.path.splitext(fname)
#     if base.endswith("_0000"):
#         base = base[:-5]

#     # ---- 骨头 ----
#     bone_out = bone_predictor(img)["instances"].to("cpu")
#     bone_masks = extract_masks(bone_out)
#     if len(bone_masks) == 0:
#         print(f"No bone detected: {img_path}")
#         return

#     # 选面积最大的骨头 mask
#     bone_mask = bone_masks[np.argmax([m.sum() for m in bone_masks])]

#     # ---- 腰大肌 ----
#     psoas_out = psoas_predictor(img)["instances"].to("cpu")
#     psoas_masks = extract_masks(psoas_out)
#     if len(psoas_masks) == 0:
#         print(f"No psoas detected: {img_path}")
#         return

#     # ---- 多 mask 核心逻辑 ----
#     best_masks, close_masks = select_psoas_masks(bone_mask, psoas_masks)

#     all_masks = best_masks + close_masks
#     all_masks = list({id(m): m for m in all_masks}.values())  # 去重

#     if len(all_masks) < 2:
#         print(f"❌ Skip: Not enough psoas: {img_path}")
#         return

#     left_main, right_main, left_group, right_group = assign_left_right_multi(
#         bone_mask, all_masks
#     )

#     if check_error_conditions_multi(bone_mask, left_main, right_main):
#         print(f"❌ Removed (bad image): {img_path}")
#         return

#     # ---- ⚠ 输出所有 psoas，而非只有 main ----
#     final_mask = np.zeros((H, W), dtype=np.uint8)

#     # 所有左侧
#     for m in left_group:
#         final_mask[m > 0] = 1

#     # 所有右侧
#     for m in right_group:
#         final_mask[m > 0] = 1

#     out_path = os.path.join(save_dir, base + ".png")
#     cv2.imwrite(out_path, final_mask * 255)

#     print(f"✔ Saved: {out_path}")


# # ============================================================
# # 5) 批处理 pipeline
# # ============================================================
# def run_psoas_pipeline(input_dir, output_dir, bone_model_path, psoas_model_path):
#     os.makedirs(output_dir, exist_ok=True)

#     bone_predictor = build_predictor(bone_model_path, score_thresh=0.5)
#     psoas_predictor = build_predictor(psoas_model_path, score_thresh=0.3)

#     for fname in sorted(os.listdir(input_dir)):
#         if fname.lower().endswith((".png", ".jpg", ".jpeg")):
#             process_single_image(
#                 os.path.join(input_dir, fname),
#                 bone_predictor,
#                 psoas_predictor,
#                 output_dir
#             )

#     print(f"\n🎉 ALL DONE! Results saved in: {output_dir}")