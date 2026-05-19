import os
import shutil

# ===============================
# 配置路径
# ===============================
SRC_DIR = "GroceryStoreDataset-master/dataset"  # 原始数据集
DST_DIR = "dataset_final"  # 扁平化后的最终目录

# 定义最终类别对应的关键字
CATEGORY_MAPPING = {
    # 水果
    "Apple": ["Apple", "Golden-Delicious", "Granny-Smith", "Pink-Lady", "Royal-Gala"],
    "Banana": ["Banana"],
    "Orange": ["Orange", "Satsumas", "Mandarin"],
    "Kiwi": ["Kiwi"],
    "Mango": ["Mango"],
    "Pineapple": ["Pineapple"],
    "Lemon": ["Lemon"],
    "Lime": ["Lime"],
    "Watermelon": ["Watermelon"],
    "Papaya": ["Papaya"],
    "Peach": ["Peach"],
    "Plum": ["Plum"],
    "Cantaloupe": ["Cantaloupe"],
    "Galia-Melon": ["Galia-Melon"],
    "Honeydew-Melon": ["Honeydew-Melon"],
    "Nectarine": ["Nectarine"],
    "Passion-Fruit": ["Passion-Fruit"],
    "Pomegranate": ["Pomegranate"],
    # 蔬菜
    "Cabbage": ["Cabbage"],
    "Carrots": ["Carrots"],
    "Cucumber": ["Cucumber"],
    "Asparagus": ["Asparagus"],
    "Leek": ["Leek"],
    "Red-Bell-Pepper": ["Red-Bell-Pepper"],
    "Green-Bell-Pepper": ["Green-Bell-Pepper"],
    "Yellow-Bell-Pepper": ["Yellow-Bell-Pepper"],
    "Beef-Tomato": ["Beef-Tomato"],
    "Regular-Tomato": ["Regular-Tomato"],
    "Zucchini": ["Zucchini"],
    "Garlic": ["Garlic"],
    "Ginger": ["Ginger"],
    "Sweet-Potato": ["Sweet-Potato"],
    "Solid-Potato": ["Solid-Potato"],
    "Floury-Potato": ["Floury-Potato"],
    "Aubergine": ["Aubergine"],
}

# 支持的图片后缀
IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp")

# ===============================
# 创建最终目录结构
# ===============================
for split in ["train", "val"]:
    for category in CATEGORY_MAPPING.keys():
        os.makedirs(os.path.join(DST_DIR, split, category), exist_ok=True)

# ===============================
# 复制图片到最终目录
# ===============================
for split in ["train", "val"]:
    src_split_dir = os.path.join(SRC_DIR, split)
    for root, dirs, files in os.walk(src_split_dir):
        for file in files:
            if not file.lower().endswith(IMG_EXTS):
                continue
            src_path = os.path.join(root, file)
            # 根据文件名/文件夹名匹配最终类别
            moved = False
            for category, keywords in CATEGORY_MAPPING.items():
                for kw in keywords:
                    if kw.lower() in file.lower() or kw.lower() in root.lower():
                        dst_path = os.path.join(DST_DIR, split, category, file)
                        shutil.copy2(src_path, dst_path)
                        moved = True
                        break
                if moved:
                    break
            if not moved:
                print(f"未匹配类别: {src_path}")

print("整理完成，最终目录在:", DST_DIR)