import os
import shutil

SRC = "dataset_flat"
DST = "dataset_merged"

for split in ["train", "val"]:
    src_split = os.path.join(SRC, split)
    dst_split = os.path.join(DST, split)

    os.makedirs(dst_split, exist_ok=True)

    for cls in os.listdir(src_split):

        # 取最终类别（第一个单词）
        main_class = cls.split("-")[0]

        src_dir = os.path.join(src_split, cls)
        dst_dir = os.path.join(dst_split, main_class)

        os.makedirs(dst_dir, exist_ok=True)

        for img in os.listdir(src_dir):
            shutil.copy(
                os.path.join(src_dir, img),
                os.path.join(dst_dir, img)
            )

print("合并完成")