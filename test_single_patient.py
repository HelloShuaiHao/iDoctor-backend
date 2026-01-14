#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：调用 all_new.main 函数处理单个患者数据
"""

import os
import sys

# 添加项目根目录到Python路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 导入处理函数
from all_new import main

# 测试数据路径（从 batch_process_all.py 中获取）
DATA_ROOT = "/media/bygpu/c61f8350-02db-4a47-88ca-3121e00c63cc1/model-code/data/2f685df1-0d89-4909-a8f3-d9bfa81a2d4d"

def test_single_patient():
    """测试单个患者数据处理"""
    print("=" * 50)
    print("开始测试单个患者数据处理")
    print("=" * 50)

    if not os.path.exists(DATA_ROOT):
        print(f"[错误] 数据根目录不存在: {DATA_ROOT}")
        return

    patient_folders = []
    for name in os.listdir(DATA_ROOT):
        folder = os.path.join(DATA_ROOT, name)
        if not os.path.isdir(folder):
            continue
        if "_" not in name:
            print(f"[跳过] 非标准命名: {name}")
            continue
        patient_folders.append(name)

    if not patient_folders:
        print("[错误] 未找到患者文件夹")
        return

    # 选择第一个患者文件夹进行测试
    folder_name = patient_folders[0]
    print(f"[测试] 选择患者: {folder_name}")

    patient_name, study_date = folder_name.split("_", 1)
    patient_folder = os.path.join(DATA_ROOT, folder_name)
    input_folder = os.path.join(patient_folder, "input")
    output_folder = os.path.join(patient_folder, "output")

    # 检查input文件夹是否存在
    if not os.path.exists(input_folder):
        print(f"[错误] input文件夹不存在: {input_folder}")
        return

    # 创建output文件夹
    os.makedirs(output_folder, exist_ok=True)

    try:
        print(f"[测试] 开始处理: {input_folder}")
        print(f"[测试] 输出目录: {output_folder}")

        # 调用 main 函数
        main(input_folder, output_folder)

        print(f"[测试] ✅ 处理成功")
    except Exception as e:
        print(f"[测试] ❌ 处理失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_single_patient()