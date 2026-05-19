import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import io
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

# 类别
classes = os.listdir(DATASET_DIR)

# 模型
model = models.resnet18(pretrained=True)
model.fc = torch.nn.Linear(model.fc.in_features, len(classes))
model.eval()

# 预处理
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])


async def predict(file):
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    img = transform(img).unsqueeze(0)

    with torch.no_grad():
        outputs = model(img)
        prob = torch.softmax(outputs, dim=1)
        confidence, predicted = torch.max(prob, 1)

    return {
        "label": classes[predicted.item()],
        "prob": float(confidence.item())
    }