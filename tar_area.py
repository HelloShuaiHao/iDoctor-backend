import os
import cv2
import numpy as np
import glob
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog
from detectron2 import model_zoo

def run_tar_area(input_folder, output_folder, weights_path):
    os.makedirs(output_folder, exist_ok=True)
    roi_info_folder = os.path.join(output_folder, "roi_info")
    os.makedirs(roi_info_folder, exist_ok=True)
    
    score_thresh = 0.5
    
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = weights_path
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thresh
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1 
    
    predictor = DefaultPredictor(cfg)

    for filename in os.listdir(input_folder):
        if not filename.lower().endswith((".jpg", ".png")):
            continue
        
        img_path = os.path.join(input_folder, filename)
        im = cv2.imread(img_path)
        if im is None:
            print(f"跳过无法读取: {filename}")
            continue
        
        H, W = im.shape[:2]
        outputs = predictor(im)
        instances = outputs["instances"].to("cpu")

        if len(instances) == 0:
            print(f"未检测到目标: {filename}, 使用整张图作为ROI")
            x1, y1, x2, y2 = 0, 0, W, H
        else:
            # ✅ 取检测到最大框
            boxes = instances.pred_boxes.tensor.numpy()
            areas = (boxes[:,2]-boxes[:,0])*(boxes[:,3]-boxes[:,1])
            idx = np.argmax(areas)
            x1, y1, x2, y2 = boxes[idx].astype(int)

        # 坐标裁图
        roi_img = im[y1:y2, x1:x2]
        if roi_img.size == 0:
            print(f"ROI区域为空: {filename}, 跳过")
            continue
        
        # ✅ 保存裁剪后的ROI
        roi_img_path = os.path.join(output_folder, filename)
        cv2.imwrite(roi_img_path, roi_img)

        # ✅ 保存ROI坐标
        txt_path = os.path.join(roi_info_folder, filename.replace(".png",".txt").replace(".jpg",".txt"))
        with open(txt_path, "w") as f:
            f.write(f"{x1} {y1} {x2} {y2}")

        print(f"已保存ROI + 坐标: {filename}")

    print("\n所有图片ROI处理完成！")


def filter_single_mask_folder(
    slice_folder,
    mask_folder,
    roi_info_folder,
    output_folder
):
    os.makedirs(output_folder, exist_ok=True)

    for fname in os.listdir(mask_folder):
        if not fname.lower().endswith(".png"):
            continue

        img_path = os.path.join(slice_folder, fname)
        mask_path = os.path.join(mask_folder, fname)
        txt_path = os.path.join(roi_info_folder, fname.replace(".png", "_0000.txt"))

        if not (os.path.exists(img_path) and os.path.exists(mask_path) and os.path.exists(txt_path)):
            print(f"[跳过] 缺失文件或ROI：{fname}")
            continue

        # === 原图尺寸 ===
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"[跳过] 原图读取失败: {fname}")
            continue
        H, W = img.shape[:2]

        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        mask_bin = (mask > 0).astype(np.uint8) * 255

        with open(txt_path, "r") as f:
            x1, y1, x2, y2 = map(int, f.readline().strip().split())

        roi_mask = np.zeros((H, W), dtype=np.uint8)
        roi_mask[y1:y2, x1:x2] = 255

        filtered_mask = cv2.bitwise_and(mask_bin, roi_mask)

        cv2.imwrite(os.path.join(output_folder, fname), filtered_mask)
        print(f"✅ 已过滤: {fname}")

    print(f"\n过滤完成! 输出位置: {output_folder}")
import os
import cv2
import glob
import numpy as np


def remove_small_components(mask, ratio=1/8):
    """
    返回:
    - cleaned: 删除小连通块后的 mask
    - removed_masks: list，每个是单独的小连通块 mask
    """
    bin_ = (mask > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_, connectivity=8)

    if num_labels <= 1:
        return mask, []

    # 最大连通块面积
    areas = stats[1:, cv2.CC_STAT_AREA]  # 排除背景
    max_area = areas.max()
    area_thresh = max_area * ratio

    cleaned = np.zeros_like(mask, dtype=np.uint8)
    removed_masks = []

    for label in range(1, num_labels):
        comp = (labels == label).astype(np.uint8)
        area = stats[label, cv2.CC_STAT_AREA]

        if area >= area_thresh:
            cleaned[comp > 0] = 255
        else:
            removed_masks.append((comp * 255).astype(np.uint8))

    return cleaned, removed_masks



def remove_small_full(input_dir, output_cleaned_dir, output_removed_dir):
    """
    input_dir: 要处理的mask目录
    output_cleaned_dir: 保留大连通块后的mask保存路径
    output_removed_dir: 被删除的小连通块保存路径
    """
    os.makedirs(output_cleaned_dir, exist_ok=True)
    os.makedirs(output_removed_dir, exist_ok=True)

    pattern = "*.png"
    ratio = 1/8

    img_paths = sorted(glob.glob(os.path.join(input_dir, pattern)))

    if not img_paths:
        print(f"[警告] 在 {input_dir} 中未找到 PNG 文件")
        return

    print(f"[信息] 共找到 {len(img_paths)} 张图片，开始处理...")

    for i, img_path in enumerate(img_paths, 1):
        fname = os.path.basename(img_path)
        mask = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

        if mask is None:
            print(f"[跳过] 无法读取：{img_path}")
            continue

        cleaned, removed_list = remove_small_components(mask, ratio=ratio)

        # 保存 cleaned mask
        cv2.imwrite(os.path.join(output_cleaned_dir, fname), cleaned)

        # 保存 removed components
        for idx, rm in enumerate(removed_list, 1):
            out_name = fname.replace(".png", f"_removed_{idx}.png")
            cv2.imwrite(os.path.join(output_removed_dir, out_name), rm)

        if i % 20 == 0 or i == len(img_paths):
            print(f"[进度] {i}/{len(img_paths)} 已完成")

    print(f"[完成] 清理后的结果保存在：{output_cleaned_dir}")
    print(f"[完成] 被删除的小块保存在：{output_removed_dir}")

def add_intersect_removed_to_filtered(hulls_output_dir, output_removed_dir, full_filtered_folder):
    """
    对每一张 hull，寻找 output_removed_dir 中对应 removed 小块，
    如果 removed 小块与 hull 存在相交，则把该 removed 小块叠加到 full_filtered_folder 对应图片上。
    """

    # 获取 hulls 列表
    hull_paths = sorted(glob.glob(os.path.join(hulls_output_dir, "*.png")))
    if not hull_paths:
        print(f"[警告] hulls_output_dir 中没有PNG文件")
        return

    # 建立 removed 小块索引: { "slice_048": [removed1.png, removed2.png] }
    removed_dict = {}
    removed_paths = sorted(glob.glob(os.path.join(output_removed_dir, "*.png")))

    for p in removed_paths:
        base = os.path.basename(p)
        key = base.split("_removed_")[0]  # slice_048
        removed_dict.setdefault(key, []).append(p)

    # 开始处理每个 hull 图
    for hull_path in hull_paths:
        hull_name = os.path.basename(hull_path)       # slice_048.png
        key = hull_name.replace(".png", "")           # slice_048

        # hull mask
        hull_mask = cv2.imread(hull_path, cv2.IMREAD_GRAYSCALE)
        if hull_mask is None:
            continue
        hull_bin = (hull_mask > 0)

        # 对应的 removed 小块
        removed_list = removed_dict.get(key, [])
        if not removed_list:
            continue

        # 对应 cleaned full mask 的路径
        cleaned_path = os.path.join(full_filtered_folder, hull_name)
        cleaned_mask = cv2.imread(cleaned_path, cv2.IMREAD_GRAYSCALE)

        if cleaned_mask is None:
            print(f"[跳过] 找不到 cleaned mask: {cleaned_path}")
            continue

        cleaned_bin = (cleaned_mask > 0)

        print(f"\n===== 处理 {hull_name} =====")

        # 遍历所有 removed 块
        for rm_path in removed_list:
            rm_mask = cv2.imread(rm_path, cv2.IMREAD_GRAYSCALE)
            if rm_mask is None:
                continue

            rm_bin = (rm_mask > 0)

            # 判断是否相交
            intersect = np.logical_and(hull_bin, rm_bin).any()

            if intersect:
                print(f"[相交] {os.path.basename(rm_path)} → 已叠加到 cleaned 图中")

                # 与 cleaned mask 叠加（OR 方式）
                cleaned_bin = np.logical_or(cleaned_bin, rm_bin)

            else:
                print(f"[无交集] {os.path.basename(rm_path)}")

        # 保存叠加后的 cleaned mask
        cleaned_final = (cleaned_bin.astype(np.uint8)) * 255
        cv2.imwrite(cleaned_path, cleaned_final)

    print("\n[完成] 所有相交的 removed 小块已合并到 full_filtered_folder 对应图片中。")


# def remove_small_components(mask_gray, ratio=1/8):
#     """
#     删除面积小于最大连通域 (max_area * ratio) 的区域
#     """
#     bin_ = (mask_gray > 0).astype(np.uint8)

#     num, labels, stats, _ = cv2.connectedComponentsWithStats(bin_, connectivity=8)
#     if num <= 1:
#         return (bin_ * 255).astype(np.uint8)

#     areas = stats[1:, cv2.CC_STAT_AREA]   # 跳过背景
#     max_area = areas.max()

#     keep = np.zeros_like(bin_)
#     for i in range(1, num):
#         if stats[i, cv2.CC_STAT_AREA] >= max_area * ratio:
#             keep[labels == i] = 1

#     return (keep * 255).astype(np.uint8)


# def remove_small_full(input_dir, output_dir):
#     os.makedirs(output_dir, exist_ok=True)
#     pattern="*.png"
#     ratio=1/8
#     img_paths = sorted(glob.glob(os.path.join(input_dir, pattern)))
#     if not img_paths:
#         print(f"[警告] 在 {input_dir} 中未找到匹配 {pattern} 的文件")
#         return

#     print(f"[信息] 共找到 {len(img_paths)} 张图片，开始处理...")

#     for i, img_path in enumerate(img_paths, 1):
#         fname = os.path.basename(img_path)
#         mask = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
#         if mask is None:
#             print(f"[跳过] 无法读取：{img_path}")
#             continue

#         cleaned = remove_small_components(mask, ratio=ratio)

#         out_path = os.path.join(output_dir, fname)
#         cv2.imwrite(out_path, cleaned)

#         if i % 20 == 0 or i == len(img_paths):
#             print(f"[进度] {i}/{len(img_paths)} 已完成")

#     print(f"[完成] 处理结束，结果已保存到：{output_dir}")


