import os
import shutil

DATA_DIR = "dataset_final"  # 你的扁平化数据集目录

for split in ["train", "val"]:
    split_dir = os.path.join(DATA_DIR, split)
    for cls in os.listdir(split_dir):
        cls_path = os.path.join(split_dir, cls)
        if os.path.isdir(cls_path):
            files = [f for f in os.listdir(cls_path) if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
            if len(files) == 0:
                print(f"删除空类别: {cls_path}")
                shutil.rmtree(cls_path)