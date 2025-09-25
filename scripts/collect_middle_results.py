import os
import csv
import shutil
import argparse
import re

def collect(data_root: str, out_root: str, summary_name: str = "汇总.csv"):
    os.makedirs(out_root, exist_ok=True)
    summary_rows = []
    header = None
    cases_processed = 0
    cases_missing_csv = 0

    date_pattern = re.compile(r'_[0-9]{8}$')  # 末尾 _YYYYMMDD

    for case_dir in sorted(os.listdir(data_root)):
        case_path = os.path.join(data_root, case_dir)
        if not os.path.isdir(case_path):
            continue

        base_id = date_pattern.sub('', case_dir)

        csv_path = os.path.join(case_path, "output", "full_overlay", "hu_statistics_middle_only.csv")
        if not os.path.isfile(csv_path):
            print(f"[WARN] 缺少: {csv_path}")
            cases_missing_csv += 1
            continue

        # 读取 CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = "\t" if "\t" in sample and sample.count("\t") >= sample.count(",") else ","
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
            if not rows:
                print(f"[WARN] 空文件: {csv_path}")
                continue
            if header is None:
                header = ["case_id"] + rows[0]
            else:
                if len(rows[0]) != len(header) - 1:
                    print(f"[WARN] 列不匹配: {csv_path}")
            for data_row in rows[1:]:
                if not data_row:
                    continue
                summary_rows.append([base_id] + data_row)

        dst_case_dir = os.path.join(out_root, base_id)
        os.makedirs(dst_case_dir, exist_ok=True)

        full_overlay_dir = os.path.join(case_path, "output", "full_overlay")
        axisal_dir = os.path.join(case_path, "output", "Axisal")
        middle_bases = set()
        copied_any = False

        # 复制 overlay 的 middle 图，重命名为 *_middle_overlay.png
        if os.path.isdir(full_overlay_dir):
            for fname in sorted(os.listdir(full_overlay_dir)):
                if fname.endswith("_middle.png"):
                    base = fname[:-len("_middle.png")]  # slice_XXX
                    src = os.path.join(full_overlay_dir, fname)
                    dst = os.path.join(dst_case_dir, f"{base}_middle_overlay.png")
                    shutil.copy2(src, dst)
                    middle_bases.add(base)
                    copied_any = True

        if not copied_any and os.path.isdir(full_overlay_dir):
            # 宽松匹配
            for fname in sorted(os.listdir(full_overlay_dir)):
                if fname.endswith(".png") and "_middle" in fname:
                    # 截取 _middle 前部分
                    base = fname.split("_middle")[0]
                    src = os.path.join(full_overlay_dir, fname)
                    dst = os.path.join(dst_case_dir, f"{base}_middle_overlay.png")
                    shutil.copy2(src, dst)
                    middle_bases.add(base)
                    copied_any = True

        if not copied_any:
            print(f"[INFO] 未找到 middle 图: {full_overlay_dir}")

        # 复制对应原始 Axisal 切片，命名 *_middle_raw.png
        if middle_bases:
            for base in sorted(middle_bases):
                orig_name = f"{base}.png"
                orig_path = os.path.join(axisal_dir, orig_name)
                if os.path.isfile(orig_path):
                    raw_dst = os.path.join(dst_case_dir, f"{base}_middle_raw.png")
                    if not os.path.isfile(raw_dst):
                        shutil.copy2(orig_path, raw_dst)
                else:
                    print(f"[WARN] 原始切片缺失: {orig_path}")

        # 复制 sagittal
        l3_overlay_dir = os.path.join(case_path, "output", "L3_overlay")
        sagittal_png = os.path.join(l3_overlay_dir, "sagittal_midResize.png")
        if os.path.isfile(sagittal_png):
            sagittal_dst = os.path.join(dst_case_dir, "sagittal_midResize.png")
            shutil.copy2(sagittal_png, sagittal_dst)
        else:
            print(f"[WARN] 缺少 sagittal_midResize.png: {l3_overlay_dir}")

            # 复制 manual_middle_mask 文件夹内容
            manual_mask_src = os.path.join(case_path, "output", "manual_middle_mask")
            manual_mask_dst = os.path.join(dst_case_dir, "manual_middle_mask")
            if os.path.isdir(manual_mask_src):
                os.makedirs(manual_mask_dst, exist_ok=True)
                for fname in sorted(os.listdir(manual_mask_src)):
                    src = os.path.join(manual_mask_src, fname)
                    dst = os.path.join(manual_mask_dst, fname)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
            else:
                print(f"[WARN] 缺少 manual_middle_mask: {manual_mask_src}")
        cases_processed += 1

    if header is None:
        print("[ERROR] 未收集到任何 CSV 数据，退出。")
        return

    summary_csv_path = os.path.join(out_root, summary_name)
    with open(summary_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(summary_rows)

    print(f"[DONE] 处理病例: {cases_processed}, 缺少 CSV: {cases_missing_csv}")
    print(f"[DONE] 汇总文件: {summary_csv_path}")
    print(f"[DONE] 汇总行数: {len(summary_rows)} (不含表头)")

def main():
    parser = argparse.ArgumentParser(description="收集中间层统计与影像")
    parser.add_argument("--data-root", default="data", help="包含各病例文件夹的根目录")
    parser.add_argument("--out-root", default="collection_results", help="汇总输出目录")
    parser.add_argument("--summary-name", default="汇总.csv", help="汇总 CSV 文件名")
    args = parser.parse_args()
    collect(args.data_root, args.out_root, args.summary_name)

if __name__ == "__main__":
    main()