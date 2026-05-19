from fastapi import APIRouter
from backend.database import SessionLocal
from backend.models import User

router = APIRouter()


@router.post("/register")
def register(data: dict):
    db = SessionLocal()

    username = data.get("username")
    password = data.get("password")

    user = User(
        username=username,
        password=password,
        role="user"  # 默认普通用户
    )

    db.add(user)
    db.commit()
    db.close()

    return {"msg": "注册成功"}


@router.post("/login")
def login(data: dict):
    db = SessionLocal()

    username = data.get("username")
    password = data.get("password")

    user = db.query(User).filter(
        User.username == username,
        User.password == password
    ).first()

    db.close()

    if user:
        return {
            "code": 200,
            "msg": "登录成功",
            "data": {
                "username": user.username,
                "role": user.role,   # ⭐关键
                "token": user.username  # ⭐先用假token（后面再升级JWT）
            }
        }
    else:
        return {
            "code": 400,
            "msg": "用户名或密码错误"
        }