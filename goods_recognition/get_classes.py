import os
import json
from torchvision import datasets

DATA_DIR = "GroceryStoreDataset-master/dataset"

dataset = datasets.ImageFolder(DATA_DIR + "/train")

print(dataset.classes)

with open("backend/classes.json","w",encoding="utf-8") as f:
    json.dump(dataset.classes,f,ensure_ascii=False)

print("classes.json 已生成")