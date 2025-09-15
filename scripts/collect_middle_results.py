import os
import csv
import shutil
import argparse
import re   # 新增

def collect(data_root: str, out_root: str, summary_name: str = "汇总.csv"):
    os.makedirs(out_root, exist_ok=True)
    summary_rows = []
    header = None
    cases_processed = 0
    cases_missing_csv = 0

    date_pattern = re.compile(r'_[0-9]{8}$')  # 匹配末尾的 _YYYYMMDD

    for case_dir in sorted(os.listdir(data_root)):
        case_path = os.path.join(data_root, case_dir)
        if not os.path.isdir(case_path):
            continue

        # 去掉末尾日期作为最终编号
        base_id = date_pattern.sub('', case_dir)

        csv_path = os.path.join(case_path, "output", "full_overlay", "hu_statistics_middle_only.csv")
        if not os.path.isfile(csv_path):
            print(f"[WARN] 缺少: {csv_path}")
            cases_missing_csv += 1
            continue

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
                # 只保留去日期后的编号列，不再写原目录名
                header = ["case_id"] + rows[0]
            else:
                if len(rows[0]) != len(header) - 1:
                    print(f"[WARN] 列不匹配: {csv_path}")
            for data_row in rows[1:]:
                if not data_row:
                    continue
                summary_rows.append([base_id] + data_row)

        # 输出目录用去日期后的 base_id（可能多个日期合并到同一目录）
        dst_case_dir = os.path.join(out_root, base_id)
        os.makedirs(dst_case_dir, exist_ok=True)

        # 1) 复制 *_middle.png
        full_overlay_dir = os.path.join(case_path, "output", "full_overlay")
        copied_any = False
        if os.path.isdir(full_overlay_dir):
            for fname in sorted(os.listdir(full_overlay_dir)):
                if fname.endswith(".png") and fname.endswith("_middle.png"):
                    src = os.path.join(full_overlay_dir, fname)
                    dst = os.path.join(dst_case_dir, fname)
                    shutil.copy2(src, dst)
                    copied_any = True
        if not copied_any:
            for fname in sorted(os.listdir(full_overlay_dir)) if os.path.isdir(full_overlay_dir) else []:
                if fname.endswith(".png") and "_middle" in fname:
                    src = os.path.join(full_overlay_dir, fname)
                    dst = os.path.join(dst_case_dir, fname)
                    shutil.copy2(src, dst)
                    copied_any = True
        if not copied_any:
            print(f"[INFO] 未找到 middle 图: {full_overlay_dir}")

        # 2) 复制 sagittal_midResize.png
        l3_overlay_dir = os.path.join(case_path, "output", "L3_overlay")
        sagittal_png = os.path.join(l3_overlay_dir, "sagittal_midResize.png")
        if os.path.isfile(sagittal_png):
            # 若已存在且来自不同日期，可选择覆盖；需要区分可改名: f"sagittal_midResize_{case_dir}.png"
            shutil.copy2(sagittal_png, os.path.join(dst_case_dir, "sagittal_midResize.png"))
        else:
            print(f"[WARN] 缺少 sagittal_midResize.png: {l3_overlay_dir}")

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