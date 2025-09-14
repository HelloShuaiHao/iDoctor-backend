import os
import argparse
import shutil

# 固定日期
FIXED_DATE = "20250914"

def is_dicom(name: str) -> bool:
    return (not name.startswith("._")) and name.lower().endswith(".dcm")

def has_any_dicom(dir_path: str) -> bool:
    for f in os.listdir(dir_path):
        if is_dicom(f):
            return True
    return False

def unique_name(parent: str, base: str) -> str:
    target = os.path.join(parent, base)
    if not os.path.exists(target):
        return target
    i = 1
    while True:
        cand = os.path.join(parent, f"{base}_{i}")
        if not os.path.exists(cand):
            return cand
        i += 1

def process_root(root: str, dry=False, force=False):
    for name in sorted(os.listdir(root)):
        old_path = os.path.join(root, name)
        if not os.path.isdir(old_path):
            continue

        # 已处理检测
        if not force and os.path.isdir(os.path.join(old_path, "input")):
            print(f"[跳过] {name} 已含 input/")
            continue

        if not has_any_dicom(old_path):
            print(f"[跳过] {name} 无 DICOM 文件")
            continue

        base_id = name.split("_")[0]
        new_folder_name = f"{base_id}_{FIXED_DATE}"
        new_path = old_path
        if os.path.basename(old_path) != new_folder_name:
            new_path = unique_name(root, new_folder_name)

        # 重命名
        if old_path != new_path:
            print(f"[重命名] {name} -> {os.path.basename(new_path)}")
            if not dry:
                os.rename(old_path, new_path)
        else:
            print(f"[保持名] {name}")

        input_dir = os.path.join(new_path, "input")
        if os.path.isdir(input_dir) and not force:
            print(f"[存在] {os.path.basename(new_path)}/input 已存在，跳过移动")
            continue

        if not dry:
            os.makedirs(input_dir, exist_ok=True)

        moved = 0
        for f in list(os.listdir(new_path)):
            full = os.path.join(new_path, f)
            if os.path.isdir(full):
                continue
            if is_dicom(f):
                if not dry:
                    shutil.move(full, os.path.join(input_dir, f))
                moved += 1
        print(f"[完成] {os.path.basename(new_path)} 迁入 {moved} 个 DICOM 到 input/ {'(dry-run)' if dry else ''}")

def main():
    ap = argparse.ArgumentParser(description="原地重构：编号 -> 编号_20250914/input (日期固定)")
    ap.add_argument("--root", default="BJData", help="BJData 根目录")
    ap.add_argument("--dry-run", action="store_true", help="仅预览不修改")
    ap.add_argument("--force", action="store_true", help="即使已有 input 也再组织一次")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        print(f"[错误] 根目录不存在: {args.root}")
        return
    process_root(args.root, dry=args.dry_run, force=args.force)

if __name__ ==