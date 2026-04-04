import os
from dotenv import load_dotenv

load_dotenv()  # fix #29: 从 .env 文件加载环境变量

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import engine, Base
from app.routers import detection, ml_detection, export

# 以 backend/ 目录为基准，不依赖启动目录
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Detection Backend", version="1.0", description="Industrial Detection Backend Service")

# 初始化数据库
Base.metadata.create_all(bind=engine)

# CORS — allow_origins=["*"] 与 allow_credentials=True 不可共存（fix B1）
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",") if o.strip()]
_allow_creds = "*" not in ALLOWED_ORIGINS  # 通配符时必须关闭 credentials

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=_allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（上传的图片等）— 使用绝对路径，不依赖启动目录
STATIC_DIR = os.path.join(BACKEND_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 路由
app.include_router(detection.router)
app.include_router(ml_detection.router)
app.include_router(export.router)


# =========================
# WebSocket 实时推送
# =========================
class ConnectionManager:
    """管理WebSocket连接"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        import json
        data = json.dumps(message, ensure_ascii=False)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                pass


ws_manager = ConnectionManager()


@app.websocket("/ws/detection")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点：实时推送检测结果"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接，等待客户端消息（心跳）
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# 暴露ws_manager供ml_detection路由使用
app.state.ws_manager = ws_manager

# 前端静态文件（优先新版 web 前端，回退到旧版 uni-app）
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "web", "dist")
WEB_DIR = os.path.abspath(WEB_DIR)
LEGACY_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "front", "dist", "build", "h5")
LEGACY_DIR = os.path.abspath(LEGACY_DIR)

FRONTEND_DIR = WEB_DIR if os.path.isdir(WEB_DIR) else LEGACY_DIR

if os.path.isdir(FRONTEND_DIR):
    assets_dir = os.path.join(FRONTEND_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def catch_all(request: Request, full_path: str):
        if full_path.startswith(("api/", "static/", "docs", "openapi")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file_path = os.path.normpath(os.path.join(FRONTEND_DIR, full_path))
        # 安全检查：确保路径不逃逸出 FRONTEND_DIR（fix #41 + fix B3）
        if file_path != FRONTEND_DIR and not file_path.startswith(FRONTEND_DIR + os.sep):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "Detection backend is running. Frontend not built yet."}
