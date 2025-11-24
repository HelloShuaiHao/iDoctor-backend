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


import cv2
import numpy as np

def select_psoas_masks(bone_mask, psoas_masks, dist_threshold=10):
    if not psoas_masks:
        return None, None, []

    # =======================================================
    # ① 找 bone 的最高点
    # =======================================================
    ys, xs = np.where(bone_mask > 0)
    if len(ys) == 0:
        return None, None, []

    bone_top_y = ys.min()
    H, W = bone_mask.shape

    # =======================================================
    # ② 初步筛选
    #   删除超过20%在骨头顶部的 
    #   删除质心在骨头内部的
    # =======================================================
    valid_masks = []

    for m in psoas_masks:
        coords = np.where(m > 0)
        ys_m = coords[0]
        xs_m = coords[1]
        if len(ys_m) == 0:
            continue

        # ----- 新规则：超过20% 的像素高于 bone_top_y 时删除 -----
        ratio_above = np.sum(ys_m < bone_top_y) / len(ys_m)
        if ratio_above > 0.20:
            continue

        # ----- 质心不能在骨头内部 -----
        cy = int(round(ys_m.mean()))
        cx = int(round(xs_m.mean()))
        if not (0 <= cy < H and 0 <= cx < W):
            continue
        if bone_mask[cy, cx] > 0:
            continue

        valid_masks.append(m)

    # =======================================================
    # ③ 若没有或只有一个，直接返回
    # =======================================================
    if len(valid_masks) == 0:
        return None, None, []

    # 仅一个合法的 mask
    if len(valid_masks) == 1:
        return valid_masks[0], None, []

    # =======================================================
    # ④ 计算骨头到 mask 的距离 transform（越小越接近骨头）
    # =======================================================
    dist_map = cv2.distanceTransform(
        (1 - bone_mask).astype(np.uint8), cv2.DIST_L2, 5
    )

    # 为每个 mask 计算平均距离
    scores = []
    min_dists = []
    for m in valid_masks:
        mask_pixels = (m > 0)
        mean_dist = dist_map[mask_pixels].mean()
        min_dist = dist_map[mask_pixels].min()  # ★ 最近距离（新增）
        scores.append((mean_dist, m))
        min_dists.append((min_dist, m))

    # 排序得到最近的两个
    scores.sort(key=lambda x: x[0])
    best1 = scores[0][1]
    best2 = scores[1][1]

    # =======================================================
    # ⑤ 新增：保留所有与骨头距离 < dist_threshold 的 mask
    # =======================================================
    additional_masks = []

    for min_dist, m in min_dists:
        if min_dist < dist_threshold:
            # 避免与 best1、best2 重复
            if not (np.array_equal(m, best1) or np.array_equal(m, best2)):
                additional_masks.append(m)

    return best1, best2, additional_masks




def assign_left_right_multiple(bone_mask, masks):
    """
    从多个 mask 中选出左右两个面积最大的 psoas。
    左边 = 所有 mask 中质心落在骨头中心左侧的最大面积块
    右边 = 所有 mask 中质心落在骨头中心右侧的最大面积块
    """

    ys, xs = np.where(bone_mask > 0)
    bone_center_x = (xs.min() + xs.max()) / 2

    left_candidates = []
    right_candidates = []

    for m in masks:
        ys_m, xs_m = np.where(m > 0)
        if len(xs_m) == 0:
            continue

        cx = xs_m.mean()
        area = len(xs_m)

        if cx < bone_center_x:
            left_candidates.append((area, m))
        else:
            right_candidates.append((area, m))

    if len(left_candidates) == 0 or len(right_candidates) == 0:
        print("❌ Error: Cannot find both left and right psoas.")
        return None, None

    # 选左右面积最大的 mask
    left_mask  = max(left_candidates,  key=lambda x: x[0])[1]
    right_mask = max(right_candidates, key=lambda x: x[0])[1]

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


def process_single_image(img_path, bone_predictor, psoas_predictor, save_dir):
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"Cannot read: {img_path}")
        return

    H, W = img.shape[:2]

    orig_name = os.path.basename(img_path)
    base, ext = os.path.splitext(orig_name)
    if base.endswith("_0000"):
        base = base[:-5]

    # ---- 骨头 ----
    bone_out = bone_predictor(img)["instances"].to("cpu")
    bone_masks = extract_masks(bone_out)
    if len(bone_masks) == 0:
        print(f"No bone detected: {img_path}")
        return
    bone_mask = bone_masks[np.argmax([m.sum() for m in bone_masks])]

    # ---- 腰大肌 ----
    psoas_out = psoas_predictor(img)["instances"].to("cpu")
    psoas_masks = extract_masks(psoas_out)
    if len(psoas_masks) == 0:
        print(f"No psoas detected: {img_path}")
        return

    best1, best2, additional_masks = select_psoas_masks(bone_mask, psoas_masks)

    if best1 is None and best2 is None:
        print(f"❌ Skip: No valid psoas after filtering → {img_path}")
        return

    # ---- 合并全部可用 mask ----
    all_masks = [m for m in [best1, best2] if m is not None] + additional_masks
    if len(all_masks) < 2:
        print(f"❌ Skip: Less than two usable masks → {img_path}")
        return

    # ---- 自动选左右两个 ----
    left_mask, right_mask = assign_left_right_multiple(bone_mask, all_masks)

    if check_error_conditions(bone_mask, left_mask, right_mask):
        print(f"❌ Removed (bad image): {img_path}")
        return

    # ---- final mask = 左右两个 + additional_masks ----
    final_mask = np.zeros((H, W), dtype=np.uint8)

    final_mask[left_mask > 0] = 1
    final_mask[right_mask > 0] = 1

    for m in additional_masks:
        final_mask[m > 0] = 1

    # ---- 保存 ----
    out_path = os.path.join(save_dir, base + ".png")
    cv2.imwrite(out_path, final_mask * 255)

    print(f"✔ Saved: {out_path}")


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
