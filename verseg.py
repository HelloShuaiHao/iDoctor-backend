import cv2
import numpy as np
import os
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog
from detectron2 import model_zoo


def get_predictor(config_file, weights, num_classes, score_thresh=0.5):
    """构建 detectron2 predictor"""
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(config_file))
    cfg.MODEL.WEIGHTS = weights
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thresh
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = num_classes
    return DefaultPredictor(cfg)

# =========================
# 辅助函数（L2–L3 模糊判断）
# =========================

def get_mask_top_bottom(mask):
    ys, xs = np.where(mask > 0)
    if len(ys) == 0:
        return None, None
    return int(ys.min()), int(ys.max())


def get_mask_x_range(mask):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None, None
    return int(xs.min()), int(xs.max())

def extract_vertical_edge(mask, mode="bottom"):
    """
    提取 mask 的真实外边缘（逐列）
    mode: "bottom" or "top"
    返回: dict { x: y }
    """
    h, w = mask.shape
    edge = {}

    for x in range(w):
        ys = np.where(mask[:, x] > 0)[0]
        if len(ys) == 0:
            continue

        if mode == "bottom":
            edge[x] = ys.max()
        else:
            edge[x] = ys.min()

    return edge


def compute_l2_l3_blur_score(
    image,
    l2_mask,
    l3_mask,
    edge_band=2
):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ---------- X 范围 ----------
    l2_x1, l2_x2 = get_mask_x_range(l2_mask)
    l3_x1, l3_x2 = get_mask_x_range(l3_mask)

    if None in [l2_x1, l3_x1]:
        return None

    x_left = max(l2_x1, l3_x1)
    x_right = min(l2_x2, l3_x2)

    if x_left >= x_right:
        return None

    # ---------- 提取真实外边缘 ----------
    l2_edge = extract_vertical_edge(l2_mask, mode="bottom")
    l3_edge = extract_vertical_edge(l3_mask, mode="top")

    L2_vals = []
    MID_vals = []
    L3_vals = []

    for x in range(x_left, x_right):
        if x not in l2_edge or x not in l3_edge:
            continue

        y2 = l2_edge[x]
        y3 = l3_edge[x]

        if y3 <= y2:
            continue

        # L2 下终板（mask 内，向上）
        for y in range(max(y2 - edge_band, 0), y2):
            if l2_mask[y, x]:
                L2_vals.append(gray[y, x])

        # L3 上终板（mask 内，向下）
        for y in range(y3, min(y3 + edge_band, gray.shape[0])):
            if l3_mask[y, x]:
                L3_vals.append(gray[y, x])

        # 中间椎间隙
        for y in range(y2 + 1, y3):
            MID_vals.append(gray[y, x])

    if len(L2_vals) == 0 or len(L3_vals) == 0 or len(MID_vals) == 0:
        return None

    mean_L2 = float(np.mean(L2_vals))
    mean_mid = float(np.mean(MID_vals))
    mean_L3 = float(np.mean(L3_vals))

    contrast_score = abs(mean_mid - mean_L2) + abs(mean_mid - mean_L3)

    return contrast_score


def l2_l3_blur_status(
    contrast_score,
    blur_thresh=60,
    warn_thresh=100
):
    """
    返回 L2–L3 清晰度状态：
      - 'blur' : 确认模糊
      - 'warn' : 警告模糊
      - 'ok'   : 清晰
    """
    if contrast_score is None:
        return "blur"

    if contrast_score < blur_thresh:
        return "blur"
    elif contrast_score < warn_thresh:
        return "warn"
    else:
        return "ok"


def visualize_l2_l3_regions(
    image,
    l2_mask,
    l3_mask,
    save_path,
    edge_band=2
):
    """
    将 L2 边缘 / 中间区域 / L3 边缘 画在一张图上并保存
    颜色约定：
      - L2 edge: 红色
      - Middle : 绿色
      - L3 edge: 蓝色
    """
    vis = image.copy()
    overlay = image.copy()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # --- X 范围（方案一） ---
    l2_x1, l2_x2 = get_mask_x_range(l2_mask)
    l3_x1, l3_x2 = get_mask_x_range(l3_mask)

    if None in [l2_x1, l3_x1]:
        return

    x_left = max(l2_x1, l3_x1)
    x_right = min(l2_x2, l3_x2)

    if x_left >= x_right:
        return

    # --- 提取真实外边缘 ---
    l2_edge = extract_vertical_edge(l2_mask, mode="bottom")
    l3_edge = extract_vertical_edge(l3_mask, mode="top")

    h, w = image.shape[:2]

    for x in range(x_left, x_right):
        if x not in l2_edge or x not in l3_edge:
            continue

        y2 = l2_edge[x]
        y3 = l3_edge[x]

        if y3 <= y2:
            continue

        # ---------- L2 下边缘（红） ----------
        for y in range(max(y2 - edge_band, 0), y2):
            if l2_mask[y, x]:
                overlay[y, x] = (0, 0, 255)  # 红

        # ---------- 中间区域（绿） ----------
        for y in range(y2 + 1, y3):
            overlay[y, x] = (0, 255, 0)  # 绿

        # ---------- L3 上边缘（蓝） ----------
        for y in range(y3, min(y3 + edge_band, h)):
            if l3_mask[y, x]:
                overlay[y, x] = (255, 0, 0)  # 蓝

    # 半透明叠加
    alpha = 0.6
    vis = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)

    cv2.imwrite(save_path, vis)


# =========================
# 主函数（已完整集成）
# =========================

def process_spine_and_vertebrae(
    img_path,
    whole_weights,
    vertebra_weights,
    output_dir
):
    """
    双模型检测流程 + L2–L3 清晰度判断
    """

    # === 读取图像 ===
    im = cv2.imread(img_path)
    if im is None:
        raise FileNotFoundError(f"未找到图像: {img_path}")

    os.makedirs(output_dir, exist_ok=True)

    config_file = "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    score_thresh = 0.5
    num_classes = 1

    # === 加载模型 ===
    whole_predictor = get_predictor(config_file, whole_weights, num_classes, score_thresh)
    vertebra_predictor = get_predictor(config_file, vertebra_weights, num_classes, score_thresh)

    # === Step 1: 整体脊柱检测 ===
    whole_outputs = whole_predictor(im)
    instances = whole_outputs["instances"].to("cpu")

    if len(instances) == 0:
        raise ValueError("未检测到脊柱！")

    spine_mask = instances.pred_masks[0].numpy().astype(np.uint8)
    spine_crop = cv2.bitwise_and(im, im, mask=spine_mask)

    # === Step 2: 椎体检测 ===
    vertebra_outputs = vertebra_predictor(spine_crop)
    vertebra_instances = vertebra_outputs["instances"].to("cpu")

    # === 可视化 ===
    v1 = Visualizer(im[:, :, ::-1], MetadataCatalog.get("wholespine_train"), scale=1.2)
    whole_overlay = v1.draw_instance_predictions(instances).get_image()[:, :, ::-1]

    v2 = Visualizer(spine_crop[:, :, ::-1], MetadataCatalog.get("newspine_train"), scale=1.2)
    vertebra_overlay = v2.draw_instance_predictions(vertebra_instances).get_image()[:, :, ::-1]

    # === 保存 ===
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_whole_overlay.png"), whole_overlay)
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_vertebra_overlay.png"), vertebra_overlay)

    # === 椎体排序 ===
    masks = vertebra_instances.pred_masks.numpy().astype(np.uint8)
    sorted_vertebrae = []

    for i, m in enumerate(masks):
        ys, xs = np.where(m > 0)
        if len(ys) == 0:
            continue
        sorted_vertebrae.append((i, np.mean(ys), m))

    sorted_vertebrae.sort(key=lambda x: x[1])

    # === 保存每个椎体 ===
    for idx, (_, _, m) in enumerate(sorted_vertebrae):
        label = f"L{idx+1}"
        cv2.imwrite(
            os.path.join(output_dir, f"{base_name}_{label}_mask.png"),
            (m * 255).astype(np.uint8)
        )
        cv2.imwrite(
            os.path.join(output_dir, f"{base_name}_{label}_overlay.png"),
            cv2.bitwise_and(im, im, mask=m)
        )

    # === L2–L3 模糊判断 ===
    contrast_score = None
    blur_status = None   # 'blur' / 'warn' / 'ok'

    if len(sorted_vertebrae) >= 3:
        _, _, L2_mask = sorted_vertebrae[1]
        _, _, L3_mask = sorted_vertebrae[2]

        contrast_score = compute_l2_l3_blur_score(
            image=im,
            l2_mask=L2_mask,
            l3_mask=L3_mask,
            edge_band=2
        )

        blur_status = l2_l3_blur_status(
            contrast_score,
            blur_thresh=60,
            warn_thresh=100
        )


    # === 可视化 L2–L3 区域（debug）===
        debug_vis_path = os.path.join(
            output_dir, f"{base_name}_L2_L3_regions_debug.png"
        )
        
        visualize_l2_l3_regions(
            image=im,
            l2_mask=L2_mask,
            l3_mask=L3_mask,
            save_path=debug_vis_path,
            edge_band=2
        )


    else:
        print("⚠️ 椎体数量不足，无法进行 L2–L3 判断")

    # === 返回结果 ===
    if len(sorted_vertebrae) >= 3:
        return {
            "L3_mask": os.path.join(output_dir, f"{base_name}_L3_mask.png"),
            "L3_overlay": os.path.join(output_dir, f"{base_name}_L3_overlay.png"),
            "whole_overlay": os.path.join(output_dir, f"{base_name}_whole_overlay.png"),
            "vertebra_overlay": os.path.join(output_dir, f"{base_name}_vertebra_overlay.png"),
            "l2_l3_blur": contrast_score,
            "blur_status": blur_status
        }
    else:
        return None
