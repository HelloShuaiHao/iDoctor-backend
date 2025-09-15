import os
import csv
import shutil
import argparse

def collect(data_root: str, out_root: str, summary_name: str = "汇总.csv"):
    os.makedirs(out_root, exist_ok=True)
    summary_rows = []
    header = None
    cases_processed = 0
    cases_missing_csv = 0

    for case_dir in sorted(os.listdir(data_root)):
        case_path = os.path.join(data_root, case_dir)
        if not os.path.isdir(case_path):
            continue

        csv_path = os.path.join(case_path, "output", "full_overlay", "hu_statistics_middle_only.csv")
        if not os.path.isfile(csv_path):
            print(f"[WARN] 缺少: {csv_path}")
            cases_missing_csv += 1
            continue

        # 读取 CSV (假定分隔符可能是逗号或制表符，做简单探测)
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
                # 校验列数
                if len(rows[0]) != len(header) - 1:
                    print(f"[WARN] 列不匹配: {csv_path}")
            # 数据行（通常只有一行；如果多行全部追加）
            for data_row in rows[1:]:
                if not data_row:
                    continue
                summary_rows.append([case_dir] + data_row)

        # 复制图片
        dst_case_dir = os.path.join(out_root, case_dir)
        os.makedirs(dst_case_dir, exist_ok=True)

        # 1) 横断面 middle 图
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
            # 兼容有的命名为 slice_XXX_middle.png 中间含 _middle
            for fname in sorted(os.listdir(full_overlay_dir)) if os.path.isdir(full_overlay_dir) else []:
                if fname.endswith(".png") and "_middle" in fname:
                    src = os.path.join(full_overlay_dir, fname)
                    dst = os.path.join(dst_case_dir, fname)
                    shutil.copy2(src, dst)
                    copied_any = True
        if not copied_any:
            print(f"[INFO] 未找到 middle 图: {full_overlay_dir}")

        # 2) 矢状图
        l3_overlay_dir = os.path.join(case_path, "output", "L3_overlay")
        sagittal_png = os.path.join(l3_overlay_dir, "sagittal_midResize.png")
        if os.path.isfile(sagittal_png):
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