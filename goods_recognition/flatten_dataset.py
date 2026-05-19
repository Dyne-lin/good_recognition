import os
import shutil

# 原始数据集路径
src_dir = "GroceryStoreDataset-master/dataset"
# 扁平化后的保存路径
dst_dir = "dataset_flat"

# 创建扁平化目录
for split in ["train", "val"]:
    src_split = os.path.join(src_dir, split)
    dst_split = os.path.join(dst_dir, split)
    os.makedirs(dst_split, exist_ok=True)

    for root, dirs, files in os.walk(src_split):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                # 取类别名为第一级子文件夹名，例如 Fruit/Apple -> Apple
                parts = os.path.normpath(root).split(os.sep)
                if len(parts) < 3:
                    continue  # 避免路径层次不够
                class_name = parts[-1]  # 最底层目录作为类别名
                class_path = os.path.join(dst_split, class_name)
                os.makedirs(class_path, exist_ok=True)
                src_file = os.path.join(root, file)
                dst_file = os.path.join(class_path, file)
                shutil.copy2(src_file, dst_file)

# 扁平化操作结束后
print("=== 扁平化完成，统计每个类别图片数量 ===")

for split in ["train", "val"]:
    split_dir = os.path.join("dataset_flat", split)
    for c in os.listdir(split_dir):
        path = os.path.join(split_dir, c)
        files = [f for f in os.listdir(path) if f.lower().endswith((".jpg",".jpeg",".png"))]
        print(split, c, len(files))