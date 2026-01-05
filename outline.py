import os
import cv2
import numpy as np
import networkx as nx
from skimage.morphology import skeletonize
from itertools import combinations


# ============================================================
# ① 多连通块：最近点连线（只做一次）
# ============================================================
def connect_components_once(mask, thickness=1):
    """
    输入: mask (灰度，白色为前景)
    输出: connected_mask (连线后的mask)
    说明: 只做一轮最近点连线，不循环。
    """
    bin_ = (mask > 0).astype(np.uint8)
    num, labels = cv2.connectedComponents(bin_)

    # num == 1: 全黑；num == 2: 只有一个前景连通块
    if num <= 2:
        return mask

    contours_list = []
    for label in range(1, num):
        comp = (labels == label).astype(np.uint8) * 255
        contours, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)
        if contours:
            contours_list.append(contours[0][:, 0, :])

    connected = mask.copy()

    # 对所有连通块轮廓做两两组合，连接最近点
    for c1, c2 in combinations(contours_list, 2):
        diff = c1[:, None, :] - c2[None, :, :]
        dist2 = np.sum(diff ** 2, axis=2)
        i, j = np.unravel_index(np.argmin(dist2), dist2.shape)
        pt1 = tuple(c1[i])
        pt2 = tuple(c2[j])
        cv2.line(connected, pt1, pt2, 255, thickness)

    return connected


# ============================================================
# ② Skeleton 全局最长路径（对整个mask找1条最长线）
# ============================================================
def longest_path_global(mask):
    """
    输入: mask (二值或灰度，>0 为前景)
    输出: (a, b): skeleton 上的两个端点 (y, x)，可能为 None
    说明: 不再按连通块拆分，而是对整个 skeleton 找一条全局最长路径。
    """
    bin_ = (mask > 0).astype(np.uint8)
    sk = skeletonize(bin_).astype(np.uint8)

    h, w = sk.shape
    G = nx.Graph()

    # 建图：每个 skeleton 像素作为节点，8邻域连边
    for y in range(h):
        for x in range(w):
            if sk[y, x]:
                G.add_node((y, x))
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx_ = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx_ < w and sk[ny, nx_]:
                            G.add_edge((y, x), (ny, nx_))

    if len(G) == 0:
        return None, None

    # 任取一个起点，第一次 BFS 找到最远点 a
    start = next(iter(G.nodes))
    lengths = nx.single_source_shortest_path_length(G, start)
    a = max(lengths, key=lengths.get)

    # 第二次 BFS，从 a 出发找到最远点 b
    lengths2 = nx.single_source_shortest_path_length(G, a)
    b = max(lengths2, key=lengths2.get)

    return a, b


# ============================================================
# ③ 外轮廓提取（最终只要这个）
# ============================================================
def extract_outer_contour(mask, thickness=2):
    """
    输入: mask (灰度/二值)
    输出: 只有外轮廓线的黑白图 (uint8, 0/255)
    """
    bin_mask = (mask > 0).astype(np.uint8) * 255
    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_NONE)
    canvas = np.zeros_like(bin_mask)
    if contours:
        cv2.drawContours(canvas, contours, -1, 255, thickness)
    return canvas


# ============================================================
# ④ 单张图的完整处理流程
# ============================================================
def final_process_mask(img, connect_thickness=1, contour_thickness=2):
    """
    img: 灰度图，白色区域为原 mask
    返回: 仅包含外轮廓线的 uint8 图像
    流程:
        - 如果有多个连通块 → 最近点连线一次
        - 然后对当前 mask skeleton → 全局最长路径 → 画中线
        - 最后对包含中线的 mask 提取外轮廓，只输出外轮廓
    """
    bin_ = (img > 0).astype(np.uint8)
    num, _ = cv2.connectedComponents(bin_)

    # Step 1: 如果是多个连通块，则先连线
    if num > 2:
        working = connect_components_once(img, thickness=connect_thickness)
    else:
        working = img.copy()

    # Step 2: 对 working 求 skeleton 的最长路径并拉一条线
    a, b = longest_path_global(working)

    tmp = working.copy()
    if a is not None and b is not None:
        # a, b 是 (y, x)，cv2 需要 (x, y)
        cv2.line(tmp, (a[1], a[0]), (b[1], b[0]), 255, 1)

    # Step 3: 只提取外轮廓作为最终输出
    contour_img = extract_outer_contour(tmp, thickness=contour_thickness)
    return contour_img


# ============================================================
# ⑤ 批量处理文件夹
# ============================================================
def batch_process_outer_contours(input_folder, output_folder,
                                connect_thickness=1,
                                contour_thickness=2):
    os.makedirs(output_folder, exist_ok=True)

    for fname in os.listdir(input_folder):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif")):
            continue

        in_path = os.path.join(input_folder, fname)
        img = cv2.imread(in_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print("跳过不可读文件:", in_path)
            continue

        contour_img = final_process_mask(
            img,
            connect_thickness=connect_thickness,
            contour_thickness=contour_thickness
        )

        out_path = os.path.join(output_folder, fname)
        cv2.imwrite(out_path, contour_img)
        print("✔ 完成:", fname)

    print("\n✅ 所有图片外轮廓处理完成，保存于:", output_folder)


# ============================================================
# 示例调用
# ============================================================
if __name__ == "__main__":
    input_folder = "./test"
    output_folder = "./test/output_contours"

    batch_process_outer_contours(input_folder, output_folder,
                                connect_thickness=1,
                                contour_thickness=2)
