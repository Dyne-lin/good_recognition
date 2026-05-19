import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
import json

# =====================
# 参数
# =====================
DATA_DIR = "dataset_final"  # 扁平化后的数据路径
BATCH_SIZE = 32
EPOCHS = 30  # 增加训练轮数
LR = 1e-3   # 预热学习率
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BEST_MODEL_PATH = "backend/best_model.pth"

# =====================
# 数据增强
# =====================
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(160),
    transforms.RandomHorizontalFlip(p=0.7),
    transforms.RandomVerticalFlip(p=0.3),
    transforms.RandomRotation(20),
    transforms.RandomAffine(degrees=20, translate=(0.1,0.1), scale=(0.9,1.1)),
    transforms.ColorJitter(0.2, 0.2, 0.2),
    transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((160,160)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
])

# =====================
# 数据加载
# =====================
train_dataset = datasets.ImageFolder(os.path.join(DATA_DIR,"train"), transform=train_transform)
val_dataset = datasets.ImageFolder(os.path.join(DATA_DIR,"val"), transform=val_transform)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)

num_classes = len(train_dataset.classes)
print("类别数量:", num_classes)
print("类别:", train_dataset.classes)

# =====================
# 模型
# =====================
model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)

# 解冻后几层卷积特征
for name, param in model.named_parameters():
    if "features.6" in name or "features.7" in name:
        param.requires_grad = True
    else:
        param.requires_grad = False

# 修改分类器
model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
model = model.to(DEVICE)

# =====================
# 损失函数 & 优化器 & 学习率调度
# =====================
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=LR, weight_decay=1e-4)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

# =====================
# 训练
# =====================
best_acc = 0
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0

    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    # 验证
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            _, predicted = torch.max(outputs,1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    acc = correct / total
    scheduler.step()

    print(f"Epoch {epoch+1}/{EPOCHS}  Loss:{total_loss:.4f}  Acc:{acc:.4f}")

    # 保存最佳模型
    if acc > best_acc:
        best_acc = acc
        torch.save(model.state_dict(), BEST_MODEL_PATH)
        print("保存最佳模型")

print("训练完成，最佳准确率:", best_acc)

# =====================
# 保存类别顺序
# =====================
with open("backend/classes.json","w",encoding="utf-8") as f:
    json.dump(train_dataset.classes, f, ensure_ascii=False)
print("类别保存完成:", train_dataset.classes)