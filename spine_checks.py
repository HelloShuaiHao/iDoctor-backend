import numpy as np

from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2 import model_zoo


_PREDICTOR_ALL = None
_PREDICTOR_WEIZHUI = None


def _build_predictor(weight_path, score_thresh=0.5):
    cfg = get_cfg()
    cfg.merge_from_file(
        model_zoo.get_config_file(
            "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
        )
    )
    cfg.MODEL.WEIGHTS = weight_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thresh
    return DefaultPredictor(cfg)


def get_spine_predictor_all(weight_path):
    global _PREDICTOR_ALL
    if _PREDICTOR_ALL is None:
        _PREDICTOR_ALL = _build_predictor(weight_path)
    return _PREDICTOR_ALL


def get_spine_predictor_weizhui(weight_path):
    global _PREDICTOR_WEIZHUI
    if _PREDICTOR_WEIZHUI is None:
        _PREDICTOR_WEIZHUI = _build_predictor(weight_path)
    return _PREDICTOR_WEIZHUI


# ============================================================
# Function 1: 检测完整脊柱 bbox
# ============================================================
def detect_spine_bbox(
    image,
    weight_all,
    min_area_ratio=0.05,
    pad=20
):
    predictor_all = get_spine_predictor_all(weight_all)

    H, W = image.shape[:2]
    outputs = predictor_all(image)
    instances = outputs["instances"].to("cpu")

    if len(instances) == 0:
        return None

    boxes = instances.pred_boxes.tensor.numpy()
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    max_idx = int(np.argmax(areas))

    if areas[max_idx] < min_area_ratio * H * W:
        return None

    x1, y1, x2, y2 = boxes[max_idx].astype(int)

    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(W, x2 + pad)
    y2 = min(H, y2 + pad)

    if x2 <= x1 or y2 <= y1:
        return None

    return (x1, y1, x2, y2)


# ============================================================
# Function 2: 判断是否包含尾椎/骶骨
# ============================================================
def contains_sacrum_or_coccyx(
    image,
    spine_bbox,
    weight_weizhui,
    score_thresh=0.5
):
    if spine_bbox is None:
        return False

    predictor_weizhui = get_spine_predictor_weizhui(weight_weizhui)

    x1, y1, x2, y2 = spine_bbox
    roi = image[y1:y2, x1:x2]

    outputs = predictor_weizhui(roi)
    instances = outputs["instances"].to("cpu")

    if len(instances) == 0:
        return False

    if instances.scores.max().item() < score_thresh:
        return False

    return True
