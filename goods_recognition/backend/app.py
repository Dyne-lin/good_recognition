# main.py
# 商品识别系统（全面升级版）
# FastAPI + SQLAlchemy + JWT认证 + 密码哈希 + 权限中间件 + 图片识别 + 历史记录

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional
import uvicorn
import os
import io
import json
import time
import hashlib
import hmac
import base64
import re

# AI识别
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# =====================================================
# 基础配置
# =====================================================
DATABASE_URL = "mysql+pymysql://root:123123@localhost:3306/goods_recognition?charset=utf8mb4"
SECRET_KEY = "your-secret-key-change-in-production-32chars"  # 生产环境请改为随机强密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

app = FastAPI(
    title="商品识别系统",
    description="基于深度学习的商品识别平台 API",
    version="2.0.0"
)

security = HTTPBearer(auto_error=False)

# =====================================================
# 跨域
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# 文件夹
# =====================================================
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# =====================================================
# 密码工具
# =====================================================
def hash_password(password: str) -> str:
    """使用 SHA-256 + HMAC 哈希密码"""
    return hmac.new(SECRET_KEY.encode(), password.encode(), hashlib.sha256).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(plain), hashed)


# =====================================================
# JWT 工具
# =====================================================
def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(s: str) -> bytes:
    padding = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    import json as _json
    header = _b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {**data, "exp": expire.timestamp(), "iat": datetime.utcnow().timestamp()}
    body = _b64encode(_json.dumps(payload).encode())
    sig = hmac.new(SECRET_KEY.encode(), f"{header}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"{header}.{body}.{sig}"


def decode_access_token(token: str) -> Optional[dict]:
    import json as _json
    try:
        header, body, sig = token.split(".")
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{header}.{body}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = _json.loads(_b64decode(body))
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        return payload
    except Exception:
        return None


# =====================================================
# 数据库模型
# =====================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class RecognitionRecord(Base):
    __tablename__ = "recognition_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    result = Column(String(100))
    confidence = Column(Float)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


Base.metadata.create_all(bind=engine)


# =====================================================
# Pydantic 模型
# =====================================================
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$")
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    username: str
    old_pwd: str
    new_pwd: str = Field(..., min_length=6, max_length=100)


class NoticeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


class AddAdminRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


# =====================================================
# 数据库依赖
# =====================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# 认证依赖
# =====================================================
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")
    return payload


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """可选认证，不强制要求登录"""
    if not credentials:
        return None
    return decode_access_token(credentials.credentials)


# =====================================================
# 加载模型
# =====================================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None
class_names = ["苹果", "香蕉", "牛奶", "面包"]

try:
    if os.path.exists("classes.json"):
        with open("classes.json", "r", encoding="utf-8") as f:
            class_names = json.load(f)

    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(class_names))

    if os.path.exists("best_model.pth"):
        model.load_state_dict(torch.load("best_model.pth", map_location=device))

    model.to(device)
    model.eval()

except Exception as e:
    print(f"模型加载失败（将使用 mock 模式）: {e}")
    model = None

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


# =====================================================
# 工具函数
# =====================================================
def ok(data=None, msg="成功"):
    return {"code": 200, "msg": msg, "data": data}


def err(msg="失败", code=400):
    return JSONResponse(status_code=code, content={"code": code, "msg": msg, "data": None})


# =====================================================
# 初始化管理员
# =====================================================
@app.get("/init_admin", tags=["系统"])
def init_admin(db: Session = Depends(get_db)):
    if db.query(Admin).first():
        return ok(msg="管理员已存在")
    db.add(Admin(username="admin", password=hash_password("123456")))
    db.commit()
    return ok(msg="初始化成功，用户名: admin，密码: 123456")


# =====================================================
# 系统状态
# =====================================================
@app.get("/status", tags=["系统"])
def system_status(db: Session = Depends(get_db)):
    return ok({
        "model_loaded": model is not None,
        "device": str(device),
        "class_count": len(class_names),
        "user_count": db.query(User).count(),
        "record_count": db.query(RecognitionRecord).count(),
        "version": "2.0.0"
    })


# =====================================================
# 注册
# =====================================================
# 保留用户名黑名单（不允许注册）
RESERVED_USERNAMES = {"admin", "root", "system", "administrator"}


@app.post("/register", tags=["认证"])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    # 检查保留用户名
    if body.username.lower() in RESERVED_USERNAMES:
        return err("该用户名不可注册")

    # 检查是否和管理员重名
    if db.query(Admin).filter(Admin.username == body.username).first():
        return err("用户名已存在")

    # 检查普通用户表
    if db.query(User).filter(User.username == body.username).first():
        return err("用户名已存在")

    db.add(User(username=body.username, password=hash_password(body.password)))
    db.commit()
    return ok(msg="注册成功")


# =====================================================
# 登录
# =====================================================
@app.post("/login", tags=["认证"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    # 普通用户
    user = db.query(User).filter(User.username == body.username).first()
    if user and verify_password(body.password, user.password):
        if not user.is_active:
            return err("账号已被禁用，请联系管理员")
        user.last_login = datetime.now()
        db.commit()
        token = create_access_token({"sub": user.username, "role": "user", "id": user.id})
        return ok({"token": token, "role": "user", "username": user.username}, "登录成功")

    # 管理员
    admin = db.query(Admin).filter(Admin.username == body.username).first()
    if admin and verify_password(body.password, admin.password):
        token = create_access_token({"sub": admin.username, "role": "admin", "id": admin.id})
        return ok({"token": token, "role": "admin", "username": admin.username}, "登录成功")

    return err("账号或密码错误")


# =====================================================
# 获取当前用户信息
# =====================================================
@app.get("/me", tags=["认证"])
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    username = current_user.get("sub")
    role = current_user.get("role")
    record_count = db.query(RecognitionRecord).filter(RecognitionRecord.created_by == username).count()
    return ok({
        "username": username,
        "role": role,
        "record_count": record_count
    })


# =====================================================
# 用户列表（仅管理员）
# =====================================================
@app.get("/users", tags=["用户管理"])
def users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(""),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    q = db.query(User)
    if keyword:
        q = q.filter(User.username.contains(keyword))
    total = q.count()
    data = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [
            {
                "id": x.id,
                "username": x.username,
                "is_active": x.is_active,
                "created_at": x.created_at.strftime("%Y-%m-%d %H:%M:%S") if x.created_at else "",
                "last_login": x.last_login.strftime("%Y-%m-%d %H:%M:%S") if x.last_login else "从未登录"
            }
            for x in data
        ]
    })


# =====================================================
# 禁用/启用用户
# =====================================================
@app.post("/toggle_user", tags=["用户管理"])
def toggle_user(
    id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return err("用户不存在")
    user.is_active = not user.is_active
    db.commit()
    status_text = "启用" if user.is_active else "禁用"
    return ok({"is_active": user.is_active}, f"已{status_text}用户 {user.username}")


# =====================================================
# 删除用户（仅管理员）
# =====================================================
@app.post("/delete_user", tags=["用户管理"])
def delete_user(
    id: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return err("用户不存在")
    db.delete(user)
    db.commit()
    return ok(msg="删除成功")


# =====================================================
# 修改密码
# =====================================================
@app.post("/change-password", tags=["认证"])
def change_password(body: ChangePasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user:
        if not verify_password(body.old_pwd, user.password):
            return err("原密码错误")
        user.password = hash_password(body.new_pwd)
        db.commit()
        return ok(msg="修改成功")

    admin = db.query(Admin).filter(Admin.username == body.username).first()
    if admin:
        if not verify_password(body.old_pwd, admin.password):
            return err("原密码错误")
        admin.password = hash_password(body.new_pwd)
        db.commit()
        return ok(msg="修改成功")

    return err("用户不存在")


# =====================================================
# 添加管理员（仅管理员）
# =====================================================
@app.post("/add-admin", tags=["用户管理"])
def add_admin(
    body: AddAdminRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    if db.query(Admin).filter(Admin.username == body.username).first():
        return err("管理员已存在")
    db.add(Admin(username=body.username, password=hash_password(body.password)))
    db.commit()
    return ok(msg="添加成功")


# =====================================================
# 图片识别
# =====================================================
@app.post("/predict", tags=["识别"])
async def predict(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 文件类型校验
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}，仅支持 JPG/PNG/GIF/WEBP")

    try:
        start = time.time()
        content = await file.read()

        # 文件大小校验
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

        # 安全文件名
        safe_name = re.sub(r"[^\w\.\-]", "_", file.filename)
        timestamp = int(time.time() * 1000)
        save_name = f"{timestamp}_{safe_name}"
        path = f"uploads/{save_name}"

        with open(path, "wb") as f:
            f.write(content)

        image = Image.open(io.BytesIO(content)).convert("RGB")

        if model:
            img = transform(image).unsqueeze(0).to(device)
            with torch.no_grad():
                out = model(img)
                probs = torch.softmax(out, dim=1)
                conf, pred = torch.max(probs, 1)
            result = class_names[pred.item()]
            confidence = float(conf.item())
            # 返回 top-3
            top3_probs, top3_idx = torch.topk(probs, min(3, len(class_names)), dim=1)
            top3 = [
                {"name": class_names[i], "confidence": round(float(p), 4)}
                for p, i in zip(top3_probs[0], top3_idx[0])
            ]
        else:
            result = "测试商品"
            confidence = 0.99
            top3 = [{"name": "测试商品", "confidence": 0.99}]

        cost = round((time.time() - start) * 1000, 2)
        creator = current_user.get("sub")

        record = RecognitionRecord(
            filename=save_name,
            result=result,
            confidence=confidence,
            created_by=creator
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return ok({
            "id": record.id,
            "result": result,
            "confidence": confidence,
            "top3": top3,
            "time": cost,
            "filename": save_name
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


# =====================================================
# 历史记录（支持分页、搜索、日期筛选）
# =====================================================
@app.get("/history", tags=["记录"])
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(""),
    date: str = Query(""),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    q = get_record_query(db, current_user)

    if keyword:
        q = q.filter(RecognitionRecord.result.contains(keyword))

    if date:
        try:
            start_dt = datetime.strptime(date, "%Y-%m-%d")
            end_dt = start_dt + timedelta(days=1)
            q = q.filter(
                RecognitionRecord.created_at >= start_dt,
                RecognitionRecord.created_at < end_dt
            )
        except:
            pass

    total = q.count()

    rows = q.order_by(RecognitionRecord.id.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return ok({
        "total": total,
        "list": [
            {
                "id": x.id,
                "filename": x.filename,
                "result": x.result,
                "confidence": x.confidence,
                "created_by": x.created_by,
                "time": x.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for x in rows
        ]
    })
def get_record_query(db, current_user):
    q = db.query(RecognitionRecord)

    username = current_user.get("sub")
    role = current_user.get("role")

    if role == "admin":
        return q  # 管理员看全部

    # 普通用户：看自己 + anonymous（兼容旧数据）
    return q.filter(
        (RecognitionRecord.created_by == username) |
        (RecognitionRecord.created_by == "anonymous")
    )

# =====================================================
# 统计数据
# =====================================================
@app.get("/stats", tags=["记录"])
def stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    q = get_record_query(db, current_user)
    records = q.all()

    today = datetime.now().date()

    count_map = {}
    today_count = 0
    daily_map = {}

    for r in records:
        # 分类统计
        count_map[r.result] = count_map.get(r.result, 0) + 1

        # 每日统计
        day_str = r.created_at.strftime("%Y-%m-%d")
        daily_map[day_str] = daily_map.get(day_str, 0) + 1

        # 今日
        if r.created_at.date() == today:
            today_count += 1

    # ========= 🔥 关键1：补齐30天 =========
    daily_trend = []
    for i in range(30):
        day = datetime.now() - timedelta(days=29 - i)
        date_str = day.strftime("%Y-%m-%d")
        daily_trend.append({
            "date": date_str,
            "count": daily_map.get(date_str, 0)
        })

    # ========= 🔥 关键2：排序分类 =========
    category_dist = sorted(
        [{"name": k, "count": v} for k, v in count_map.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    return ok({
        "total": len(records),
        "today": today_count,
        "category_dist": category_dist,
        "daily_trend": daily_trend
    })


# =====================================================
# 删除单条记录
# =====================================================
@app.delete("/history/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    row = db.query(RecognitionRecord).filter(RecognitionRecord.id == record_id).first()
    if not row:
        return err("记录不存在")

    username = current_user.get("sub")
    role = current_user.get("role")

    if role != "admin" and row.created_by not in [username, "anonymous"]:
        return err("无权限删除", 403)

    db.delete(row)
    db.commit()
    return ok(msg="删除成功")


# =====================================================
# 清空记录（仅管理员）
# =====================================================
@app.post("/clear", tags=["记录"])
def clear(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    count = db.query(RecognitionRecord).count()
    db.query(RecognitionRecord).delete()
    db.commit()
    return ok(msg=f"已清空 {count} 条记录")


# =====================================================
# 查看图片
# =====================================================
@app.get("/preview", tags=["识别"])
def preview(filename: str):
    # 防止路径穿越
    safe_name = os.path.basename(filename)
    path = f"uploads/{safe_name}"
    if not os.path.exists(path):
        raise HTTPException(404, "文件不存在")
    return FileResponse(path)


# =====================================================
# 公告 API
# =====================================================
@app.get("/notice_list", tags=["公告"])
def notice_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    total = db.query(Notice).count()
    rows = db.query(Notice).order_by(Notice.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "total": total,
        "list": [
            {
                "id": x.id,
                "title": x.title,
                "content": x.content,
                "author": x.author or "管理员",
                "time": x.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for x in rows
        ]
    })


@app.get("/notice", tags=["公告"])
def get_notice(db: Session = Depends(get_db)):
    data = db.query(Notice).order_by(Notice.id.desc()).first()
    if not data:
        return ok({"title": "系统公告", "content": "暂无公告", "time": ""})
    return ok({
        "id": data.id,
        "title": data.title,
        "content": data.content,
        "author": data.author or "管理员",
        "time": data.created_at.strftime("%Y-%m-%d %H:%M:%S")
    })


@app.post("/save_notice", tags=["公告"])
def save_notice(
    body: NoticeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    obj = Notice(title=body.title, content=body.content, author=current_user.get("sub"))
    db.add(obj)
    db.commit()
    return ok(msg="发布成功")


@app.post("/delete_notice_by_id", tags=["公告"])
def delete_notice_by_id(
    id: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    row = db.query(Notice).filter(Notice.id == id).first()
    if not row:
        return err("公告不存在")
    db.delete(row)
    db.commit()
    return ok(msg="删除成功")


@app.post("/clear_all_notices", tags=["公告"])
def clear_all_notices(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    db.query(Notice).delete()
    db.commit()
    return ok(msg="已清空所有公告")


# =====================================================
# 启动
# =====================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",        # ← 改成字符串形式："文件名:变量名"
        host="127.0.0.1",
        port=8000,
        reload=True       # 现在 reload 可以正常使用了
    )