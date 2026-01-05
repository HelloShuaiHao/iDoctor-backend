# import os
# import cv2
# import numpy as np
# from skimage.morphology import skeletonize
# import networkx as nx

# def longest_path(mask):
#     h, w = mask.shape
#     sk = skeletonize(mask).astype(np.uint8)
#     G = nx.Graph()

#     for y in range(h):
#         for x in range(w):
#             if sk[y, x]:
#                 G.add_node((y, x))
#                 for dy in [-1, 0, 1]:
#                     for dx in [-1, 0, 1]:
#                         if dy == 0 and dx == 0:
#                             continue
#                         ny, nx_ = y + dy, x + dx
#                         if 0 <= ny < h and 0 <= nx_ < w and sk[ny, nx_]:
#                             G.add_edge((y, x), (ny, nx_))

#     if len(G) == 0:
#         return [], None, None

#     start = list(G.nodes)[0]
#     lengths = nx.single_source_shortest_path_length(G, start)
#     a = max(lengths, key=lengths.get)

#     lengths2 = nx.single_source_shortest_path_length(G, a)
#     b = max(lengths2, key=lengths2.get)

#     path = nx.shortest_path(G, a, b)
#     return path, a, b

# def process_image(path, save_dir):
#     name = os.path.splitext(os.path.basename(path))[0]
#     img = cv2.imread(path, 0)
#     bin_img = img > 0
#     h, w = img.shape

#     num, lbl = cv2.connectedComponents(bin_img.astype(np.uint8))

#     center_endpoints = []  # [(a,b), (a,b), ...]

#     for cid in range(1, num):  # 跳过背景
#         comp = (lbl == cid)
#         path_pts, a, b = longest_path(comp)
#         if path_pts and a is not None and b is not None:
#             center_endpoints.append((a, b))

#     combined = img.copy()


#     if len(center_endpoints) == 1:
#         a, b = center_endpoints[0]
#         cv2.line(combined, (a[1], a[0]), (b[1], b[0]), 255, 1)

#     elif len(center_endpoints) > 1:

#         for i, (a1, b1) in enumerate(center_endpoints):
#             for p1 in [a1, b1]:

#                 if p1 is None:
#                     continue

#                 dmin = 1e9
#                 best = None

#                 for j, (a2, b2) in enumerate(center_endpoints):
#                     if i == j:
#                         continue

#                     for p2 in [a2, b2]:
#                         if p2 is None:
#                             continue

#                         d = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
#                         if d < dmin:
#                             dmin = d
#                             best = (p1, p2)

#                 if best is None:
#                     continue

#                 (y1, x1), (y2, x2) = best
#                 cv2.line(combined, (x1, y1), (x2, y2), 255, 1)

#     contours, _ = cv2.findContours((combined > 0).astype(np.uint8),
#                                    cv2.RETR_EXTERNAL,
#                                    cv2.CHAIN_APPROX_NONE)

#     contour_img = np.zeros((h, w), dtype=np.uint8)
#     cv2.drawContours(contour_img, contours, -1, 255, 1)

#     out_path = os.path.join(save_dir, f"{name}_contour.png")
#     cv2.imwrite(out_path, contour_img)
#     print("✔ 输出Contour:", out_path)

# def batch_process_masks(input_dir, output_dir):
#     os.makedirs(output_dir, exist_ok=True)

#     for fname in os.listdir(input_dir):
#         if fname.lower().endswith((".png", ".jpg", ".jpeg")):
#             fpath = os.path.join(input_dir, fname)
#             print("处理:", fpath)
#             process_image(fpath, output_dir)

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



def hull_to_mask(hull_img):
    if len(hull_img.shape) == 3:
        gray = cv2.cvtColor(hull_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = hull_img.copy()

    h, w = gray.shape

    line_mask = (gray > 127).astype(np.uint8) * 255

    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print("⚠️ No contour found.")
        return None

    hull = max(contours, key=cv2.contourArea)

    inside_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(inside_mask, [hull], -1, 255, thickness=-1)

    return inside_mask

def split_sat_vat(full_mask_path, hull_img_path, save_sat_path, save_vat_path):

    full_mask = cv2.imread(full_mask_path, cv2.IMREAD_GRAYSCALE)
    hull_img = cv2.imread(hull_img_path)

    if full_mask is None or hull_img is None:
        print("[ERROR] Cannot read:", full_mask_path)
        return

    if len(hull_img.shape) == 3:
        gray = cv2.cvtColor(hull_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = hull_img

    line_mask = (gray > 127).astype(np.uint8) * 255 
    inside_mask = hull_to_mask(hull_img)  
    inside_bool = inside_mask > 0

    full_bool = full_mask > 0

    vat = np.zeros_like(full_mask)
    vat[full_bool & inside_bool] = 255

    sat = np.zeros_like(full_mask)
    sat[full_bool & (~inside_bool)] = 255

    # sat[line_mask == 255] = 255
    valid_line = np.zeros_like(line_mask)
    valid_line[(line_mask == 255) & (full_mask > 0)] = 255

    # 只把有效轮廓画入 SAT
    sat[valid_line == 255] = 255

    cv2.imwrite(save_vat_path, vat)
    cv2.imwrite(save_sat_path, sat)

    return sat, vat

def batch_split_sat_vat(full_mask_dir, hull_dir, out_sat_dir, out_vat_dir):
    os.makedirs(out_sat_dir, exist_ok=True)
    os.makedirs(out_vat_dir, exist_ok=True)

    valid_ext = (".png", ".jpg", ".jpeg", ".bmp")

    for name in os.listdir(full_mask_dir):
        if not name.lower().endswith(valid_ext):
            continue

        full_mask_path = os.path.join(full_mask_dir, name)
        hull_img_path = os.path.join(hull_dir, name)

        if not os.path.exists(hull_img_path):
            print("[SKIP] No hull for:", name)
            continue

        save_sat = os.path.join(out_sat_dir, name)
        save_vat = os.path.join(out_vat_dir, name)

        print("[PROCESS]", name)
        split_sat_vat(full_mask_path, hull_img_path, save_sat, save_vat)

    print("\n✔ SAT / VAT 分割完成！")

