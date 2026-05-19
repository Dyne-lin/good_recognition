# 商品识别系统 (Goods Recognition System)

基于深度学习的商品识别平台，支持图像上传、AI识别、用户认证和历史记录管理。

## 📋 项目简介

本项目是一个完整的商品识别系统，使用 FastAPI 构建后端服务，结合 PyTorch 深度学习框架实现商品图像识别功能。

## 🛠️ 技术栈

- **后端框架**: FastAPI 0.135.3
- **深度学习**: PyTorch 2.11.0 + TorchVision 0.26.0
- **数据库**: MySQL + SQLAlchemy 2.0
- **认证方式**: JWT Token
- **图像处理**: Pillow 12.2.0
- **服务器**: Uvicorn 0.42.0

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 MariaDB
- Git

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/Dyne-lin/good_recognition.git
cd good_recognition
```

2. **创建虚拟环境**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置数据库**

创建 MySQL 数据库：

```sql
CREATE DATABASE goods_recognition CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改 `backend/app.py` 中的数据库连接配置：

```python
DATABASE_URL = "mysql+pymysql://用户名:密码@localhost:3306/goods_recognition?charset=utf8mb4"
```

5. **启动服务**

```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：
- API文档: http://localhost:8000/docs
- 前端页面: http://localhost:8000/

## 🔌 API 接口

### 用户认证

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/register` | POST | 用户注册 |
| `/api/login` | POST | 用户登录 |
| `/api/logout` | POST | 用户登出 |

### 商品识别

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/predict` | POST | 上传图片进行识别 |
| `/api/history` | GET | 获取识别历史记录 |
| `/api/history/{id}` | DELETE | 删除单条历史记录 |

### 接口示例

**用户注册**
```bash
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'
```

**图片识别**
```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@apple.jpg"
```

## 📁 项目结构

```
goods_recognition/
├── backend/                  # 后端服务
│   ├── app.py               # FastAPI 主应用
│   ├── model.py             # 深度学习模型
│   ├── predict.py           # 预测逻辑
│   ├── auth.py              # 认证模块
│   ├── database.py          # 数据库配置
│   ├── models.py            # SQLAlchemy 模型
│   ├── classes.json         # 商品类别配置
│   ├── best_model.pth       # 训练好的模型权重
│   └── uploads/             # 上传文件存储
├── frontend/                # 前端页面
│   ├── index.html           # 主页面
│   └── login.html           # 登录页面
├── dataset_final/           # 训练数据集
├── train.py                 # 模型训练脚本
├── requirements.txt         # Python 依赖
└── README.md               # 项目说明文档
```

## 🧠 识别类别

系统支持识别多种商品类别，包括但不限于：

- **水果类**: Apple, Banana, Orange, Lemon, Mango, Kiwi, Watermelon...
- **蔬菜类**: Cabbage, Carrots, Cucumber, Tomato, Bell Pepper...
- **其他**: Potato, Ginger, Garlic...

完整类别列表请查看 `backend/classes.json`。

## 📊 模型训练

如需重新训练模型：

```bash
python train.py --epochs 50 --batch-size 32 --lr 0.001
```

## 📝 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目地址**: https://github.com/Dyne-lin/good_recognition
