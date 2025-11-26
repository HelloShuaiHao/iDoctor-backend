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


def process_spine_and_vertebrae(
    img_path,
    whole_weights,
    vertebra_weights,
    output_dir
):
    """
    双模型检测流程：
    1. 用第一个模型检测整条脊柱；
    2. 用第二个模型检测椎体；
    3. 保存检测结果、裁剪图、每个椎体mask；
    4. 椎体从上到下排序命名 L1, L2, L3, ...

    参数：
        img_path: 输入图像路径
        whole_weights: 整体脊柱模型权重路径
        vertebra_weights: 椎体检测模型权重路径
        L3_mask: 输出目录
        L3_overlay: L3椎体检测结果图
        whole_overlay: 整脊柱检测结果图
        vertebra_overlay: 椎体检测结果图
    """
    # === 读取图像 ===
    im = cv2.imread(img_path)
    if im is None:
        raise FileNotFoundError(f"未找到图像: {img_path}")

    os.makedirs(output_dir, exist_ok=True)

    config_file="COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    score_thresh=0.5
    num_classes=1

    # === 加载两个模型 ===
    whole_predictor = get_predictor(config_file, whole_weights, num_classes, score_thresh)
    vertebra_predictor = get_predictor(config_file, vertebra_weights, num_classes, score_thresh)

    # === 第一步：检测整条脊柱 ===
    whole_outputs = whole_predictor(im)
    instances = whole_outputs["instances"].to("cpu")

    if len(instances) == 0:
        raise ValueError("未检测到脊柱！")

    # 假设只有一个脊柱实例
    mask = instances.pred_masks[0].numpy().astype(np.uint8)

    # === 用 mask 裁剪出脊柱区域 ===
    spine_crop = cv2.bitwise_and(im, im, mask=mask)

    # === 第二步：检测椎体 ===
    vertebra_outputs = vertebra_predictor(spine_crop)
    vertebra_instances = vertebra_outputs["instances"].to("cpu")

    # === 可视化结果 ===
    v1 = Visualizer(im[:, :, ::-1], MetadataCatalog.get("wholespine_train"), scale=1.2)
    out1 = v1.draw_instance_predictions(instances)
    whole_overlay = out1.get_image()[:, :, ::-1]
    
    v2 = Visualizer(spine_crop[:, :, ::-1], MetadataCatalog.get("newspine_train"), scale=1.2)
    out2 = v2.draw_instance_predictions(vertebra_instances)
    vertebra_overlay = out2.get_image()[:, :, ::-1]

    # === 保存结果 ===
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_whole.png"), out1.get_image()[:, :, ::-1])
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_spine_crop.png"), spine_crop)
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_vertebra.png"), out2.get_image()[:, :, ::-1])

    # === 提取每个椎体 mask 并按Y坐标排序 ===
    masks = vertebra_instances.pred_masks.numpy().astype(np.uint8)
    sorted_vertebrae = []
    for i, m in enumerate(masks):
        ys, xs = np.where(m > 0)
        if len(ys) == 0:
            continue
        centroid_y = np.mean(ys)
        sorted_vertebrae.append((i, centroid_y, m))

    sorted_vertebrae.sort(key=lambda x: x[1])

    for idx, (i, cy, m) in enumerate(sorted_vertebrae):
        label = f"L{idx+1}"
        mask_img = (m * 255).astype(np.uint8)
        overlay_img = cv2.bitwise_and(im, im, mask=m)

        cv2.imwrite(os.path.join(output_dir, f"{base_name}_{label}_mask.png"), mask_img)
        cv2.imwrite(os.path.join(output_dir, f"{base_name}_{label}_overlay.png"), overlay_img)

    # === Step 5: 保存整体 overlay 图 ===
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_whole_overlay.png"), whole_overlay)
    cv2.imwrite(os.path.join(output_dir, f"{base_name}_vertebra_overlay.png"), vertebra_overlay)

    print(f"✅ 已完成处理: {img_path}")
    print(f"结果保存在 {output_dir}/")
    
    # === ✅ 仅提取并返回 L3 相关结果（返回路径，不再重复保存） ===
    if len(sorted_vertebrae) >= 3:
        _, _, L3_mask_array = sorted_vertebrae[2]  # 第3个是L3
        label = "L3"

        base_name = os.path.splitext(os.path.basename(img_path))[0]
        L3_mask_path = os.path.join(output_dir, f"{base_name}_{label}_mask.png")
        L3_overlay_path = os.path.join(output_dir, f"{base_name}_{label}_overlay.png")
        whole_overlay_path = os.path.join(output_dir, f"{base_name}_whole_overlay.png")
        vertebra_overlay_path = os.path.join(output_dir, f"{base_name}_vertebra_overlay.png")

        # ✅ 直接返回路径（这些文件前面都已经保存过）
        return {
            "L3_mask": L3_mask_path,
            "L3_overlay": L3_overlay_path,
            "whole_overlay": whole_overlay_path,
            "vertebra_overlay": vertebra_overlay_path
        }

    else:
        print("⚠️ 检测到的椎体数量不足，无法提取 L3。")
        return None
