import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine, Base
from app.routers import detection, ml_detection

app = FastAPI(title="Detection Backend", version="1.0", description="Industrial Detection Backend Service")

# 初始化数据库
Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（上传的图片等）
app.mount("/static", StaticFiles(directory="static"), name="static")

# 路由
app.include_router(detection.router)
app.include_router(ml_detection.router)

# 前端H5静态文件
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "front", "dist", "build", "h5")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

if os.path.isdir(FRONTEND_DIR):
    # 挂载前端的 assets 目录
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="frontend_assets")

    # 挂载前端的 uni_modules 目录（如果存在）
    uni_modules_dir = os.path.join(FRONTEND_DIR, "uni_modules")
    if os.path.isdir(uni_modules_dir):
        app.mount("/uni_modules", StaticFiles(directory=uni_modules_dir), name="frontend_uni_modules")

    # 前端静态资源
    frontend_static = os.path.join(FRONTEND_DIR, "static")
    if os.path.isdir(frontend_static):
        app.mount("/frontend_static", StaticFiles(directory=frontend_static), name="frontend_static_files")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    # 捕获所有非API路由，返回前端index.html（SPA路由支持）
    @app.get("/{full_path:path}")
    async def catch_all(request: Request, full_path: str):
        # 如果是API路径，跳过
        if full_path.startswith("api/") or full_path.startswith("static/") or full_path.startswith("docs") or full_path.startswith("openapi"):
            return {"detail": "Not Found"}

        # 检查是否是前端目录下的实际文件
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # 否则返回index.html（SPA路由）
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "Detection backend is running. Frontend not built yet."}