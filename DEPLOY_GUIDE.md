# 产品能效标签智能检测系统 — 部署指南

> 第十七届中国大学生服务外包创新创业大赛 · A02 · 诚迈科技命题
> 本文档面向所有团队成员，从 GitHub 拉取代码后按步骤完成各端的部署和联调。
> 开发文档（架构、API、数据流等）请看同目录下的 `DEV_DOC.md`。

---

## 〇、文档导航

| 文档 | 说明 |
|------|------|
| `DEPLOY_GUIDE.md`（本文档） | 全端部署指南，保姆级，从零到跑通 |
| `DEV_DOC.md` | 完整技术参考（架构设计、API 接口、数据流、ML 引擎等） |
| `LOCAL_FILES_CHECKLIST.md` | 被 gitignore 排除的本地文件备份清单 |

**部署优先级**：

| 顺序 | 模块 | 标记 | 说明 |
|------|------|------|------|
| 1 | 后端 | ⚙️ **必备** | 所有前端都依赖后端，必须先部署 |
| 2 | OpenHarmony 鸿蒙端 | ⭐ **必选** | 比赛核心，部署到 DAYU200 开发板 |
| 3 | Web 前端 | 🏅 **推荐** | 电脑大屏演示、多端协同展示 |
| 4 | uni-app 移动端 | 💡 加分项 | 展示多端覆盖能力 |
| 5 | Docker | 💡 加分项 | 展示容器化部署能力 |

---

## 一、拉取代码

```bash
git clone https://github.com/Stardep-lmc/EnergyLabel-Detection-System.git
cd EnergyLabel-Detection-System
```

拉取后目录结构：

```
EnergyLabel-Detection-System/
├── Service-Outsourcing/          # 主应用
│   ├── backend/                  # FastAPI 后端（Python）
│   │   ├── main.py              # 入口
│   │   ├── requirements.txt     # 核心依赖
│   │   ├── requirements-ml.txt  # ML 依赖
│   │   ├── app/                 # 业务代码
│   │   ├── static/uploads/      # 上传图片存储
│   │   └── tests/               # 测试
│   ├── frontend/
│   │   ├── web/                 # Vue 3 Web 前端（主力）
│   │   ├── front/               # uni-app 移动端
│   │   └── front-homo/          # OpenHarmony 鸿蒙端
│   ├── Dockerfile               # Docker 镜像
│   └── docker-compose.yml       # Docker Compose 编排
│
├── yolo-distiller/               # YOLO 知识蒸馏训练框架
│   ├── scripts/                  # 训练/推理脚本
│   ├── ultralytics/              # 修改版 ultralytics（支持蒸馏）
│   └── runs/                     # 训练输出（模型权重）
│
├── DEV_DOC.md                    # 开发文档
└── DEPLOY_GUIDE.md               # 本文档
```

---

## 二、后端部署（必须先完成，所有前端都依赖后端）

### 2.1 环境要求

| 项目 | 要求 | 备注 |
|------|------|------|
| 操作系统 | Linux / macOS / Windows | 推荐 Linux |
| Python | 3.9+（推荐 3.9） | 推荐用 conda 管理 |
| GPU | 可选 | 有 CUDA GPU 推理更快，CPU 也能跑（首次推理约 4 秒，后续约 100ms） |
| 内存 | 4GB+ | 模型加载约占 200MB |
| 磁盘 | 模型权重约 50MB | |

### 2.2 安装 conda（如果没有）

```bash
# Linux / macOS
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# 按提示完成安装，重启终端

# 验证
conda --version
```

### 2.3 创建 conda 环境

如果你的机器已经有 `yolo_distiller_lmc` 环境，直接 `conda activate yolo_distiller_lmc` 跳到 2.4。

```bash
# 创建环境
conda create -n yolo_distiller_lmc python=3.9 -y

# 激活环境（每次打开新终端都要执行）
conda activate yolo_distiller_lmc

# 安装 PyTorch（根据你的 CUDA 版本选择一行执行）

# 有 NVIDIA GPU + CUDA 12.x:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# 有 NVIDIA GPU + CUDA 11.8:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 没有 GPU（仅 CPU）:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 验证 PyTorch
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

### 2.4 安装后端依赖

```bash
# 确保在项目根目录
cd Service-Outsourcing/backend

# 核心依赖（FastAPI、SQLAlchemy、Pydantic 等）
pip install -r requirements.txt

# ML 依赖（ultralytics YOLO、OpenCV 等）
pip install -r requirements-ml.txt

# 可选：PaddleOCR（OCR 文字识别功能）
# 不装也能跑，ML 检测正常工作，只是 OCR 会用降级模式（显示"x级能效"而非真实识别文本）
# pip install paddleocr paddlepaddle

# 验证所有依赖
python -c "import fastapi, sqlalchemy, torch, ultralytics; print('所有依赖安装成功')"
```

### 2.5 获取模型权重（重要！）

模型权重文件（`best.pt`，约 5MB）太大不在 Git 仓库中，需要单独获取。

**方式一：从团队网盘下载（推荐）**

1. 从团队共享网盘下载 `best.pt`
2. 放到指定路径：

```bash
# 回到项目根目录
cd ../..

# 创建目录（如果不存在）
mkdir -p yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/

# 复制模型文件
cp ~/Downloads/best.pt yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt

# 验证
ls -la yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt
# 应显示文件大小约 5.3MB
```

**方式二：不放模型（临时方案）**

后端仍可正常启动，配置、历史、统计等 API 全部正常，但 `/api/ml/detect`（图片检测）会返回 503。

**方式三：自行训练（需要 GPU）**

参考 `DEV_DOC.md` 第五节 ML 引擎详解，约需 GPU 16 小时。

### 2.6 启动后端

```bash
cd Service-Outsourcing/backend

# 确保激活了正确的 conda 环境
conda activate yolo_distiller_lmc

# 开发模式（代码修改后自动重载，推荐开发时用）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 或生产模式（更稳定）
uvicorn main:app --host 0.0.0.0 --port 8000
```

启动成功后你会看到类似输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:ml_detection:加载Student DPFD模型: .../yolo11n_dpfd_energy_label/weights/best.pt
INFO:inference_service:检测器初始化完成
```

> ⚠️ **必须用 `--host 0.0.0.0`**，否则其他设备（开发板、手机、其他电脑）无法访问后端。
> ⚠️ **不要关闭这个终端**，后端需要一直运行。

### 2.7 验证后端是否正常

打开另一个终端：

```bash
# 1. 测试基础 API（应返回 JSON 配置）
curl http://localhost:8000/api/config

# 2. 测试 ML 状态（应返回 available: true）
curl http://localhost:8000/api/ml/status

# 3. 测试图片检测（如果有测试图片）
curl -X POST http://localhost:8000/api/ml/detect \
  -F "file=@你的测试图片.jpg"

# 4. 打开浏览器访问 API 文档
# http://localhost:8000/docs
```

### 2.8 查看后端 IP（给其他端用）

其他前端（Web、鸿蒙、uni-app）需要知道后端的局域网 IP：

```bash
# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1
# 输出类似：inet 192.168.1.100/24

# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

**记下你的 IP**（如 `192.168.1.100`），后面各前端配置都要用。

验证其他设备能访问：

```bash
# 在其他设备上执行（把 IP 换成你的）
curl http://192.168.1.100:8000/api/config
# 如果返回 JSON，说明网络通了
```

如果访问不了，检查防火墙：

```bash
# Linux
sudo ufw allow 8000
# 或
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

---

## 三、⭐ OpenHarmony 鸿蒙端部署（必选，比赛核心）

### 3.1 硬件要求

| 设备 | 要求 |
|------|------|
| 开发板 | DAYU200 (HH-SCDAYU200)，已刷入 OpenHarmony 4.0+ 系统镜像 |
| 电脑 | Windows 10/11 或 macOS 12+，8GB+ 内存 |
| USB 线 | **支持数据传输**的 USB-A to USB-C 线（不能是仅充电线！） |
| 网络 | 开发板和后端服务器在**同一局域网**（WiFi 或有线） |
| 显示器 | HDMI 显示器（连接开发板查看 UI） |

### 3.2 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| DevEco Studio | 4.0+ | 华为官方 IDE |
| OpenHarmony SDK | API 10+ | DevEco Studio 首次启动时自动安装 |
| Node.js | 16+ | DevEco Studio 自带，无需单独安装 |
| ohpm | 自带 | OpenHarmony 包管理器 |
| hdc | 自带 | 设备调试工具 |

### 3.3 安装 DevEco Studio

1. 下载地址：https://developer.huawei.com/consumer/cn/deveco-studio/
2. 安装后首次启动，按向导完成：
   - **选择 OpenHarmony 开发模式**（不是 HarmonyOS！这两个不一样）
   - 安装 OpenHarmony SDK，选择 **API 10** 或以上
   - 等待 Node.js、ohpm 自动配置完成（约 5-10 分钟）
3. 验证安装：File → Settings → OpenHarmony SDK，确认 SDK 路径和版本号

### 3.4 打开项目

1. 启动 DevEco Studio
2. File → Open → 选择 `Service-Outsourcing/frontend/front-homo` 目录
3. 等待 Sync 完成（首次会下载依赖，约 2-5 分钟）
4. 如果提示 SDK 版本不匹配，按提示更新 SDK
5. 如果 ohpm install 失败，检查网络连接，或手动执行：
   ```bash
   cd Service-Outsourcing/frontend/front-homo
   ohpm install
   ```

### 3.5 配置后端地址（关键步骤！）

需要修改**两个文件**，把 `localhost` 改成后端的实际 IP：

**文件 1：`empty/src/main/ets/common/Api.ets`**

找到第 4 行左右：

```typescript
// 将 localhost 改为后端实际 IP
const BASE_URL: string = 'http://192.168.1.100:8000';  // ← 改成你的后端 IP
```

**文件 2：`empty/src/main/ets/common/WebSocketClient.ets`**

找到 WS URL 配置：

```typescript
// 将 localhost 改为后端实际 IP
const WS_URL: string = 'ws://192.168.1.100:8000/ws/detection';  // ← 改成你的后端 IP
```

> ⚠️ 两个文件的 IP 必须一致！
> ⚠️ 后端必须以 `--host 0.0.0.0` 启动才能被开发板访问！

### 3.6 连接开发板

**USB 连接：**

1. USB 线连接 DAYU200 到电脑
2. 确认开发板已开机（屏幕亮起，或 HDMI 显示器有画面）
3. 打开终端验证：

```bash
hdc list targets
```

应输出设备序列号，如 `7001005458323933328a01e4e3825800`。

**连接失败排查：**

| 问题 | 解决方案 |
|------|----------|
| `[Empty]` 无设备 | 检查 USB 线是否支持数据传输；换 USB 口试试 |
| Windows 无法识别 | 安装 HDC USB 驱动：DevEco Studio → Tools → Device Manager → Install Driver |
| macOS 无法识别 | 系统偏好设置 → 安全性与隐私 → 允许 HDC 访问 |
| 设备离线 | 重启开发板；重新插拔 USB；执行 `hdc kill` 后重试 |

**WiFi 调试（可选，不想一直插 USB 线时用）：**

```bash
# 先通过 USB 连接，获取开发板 IP
hdc shell ifconfig
# 找到 wlan0 的 inet addr，如 192.168.1.200

# 开启 TCP 调试
hdc tconn 192.168.1.200:5555

# 之后可以拔掉 USB，通过 WiFi 调试
hdc list targets  # 应显示 192.168.1.200:5555
```

### 3.7 编译部署到开发板

1. DevEco Studio 顶部工具栏，选择目标设备（应显示你的 DAYU200）
2. 选择 `empty` 模块
3. 点击 ▶ Run 按钮（或 Shift+F10）
4. 等待编译完成，应用会自动安装到开发板并启动

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 首次编译 | 2-3 分钟 | 需要编译所有模块 |
| 增量编译 | 10-30 秒 | 只编译修改的文件 |
| 安装到设备 | 5-10 秒 | 通过 hdc 推送 HAP 包 |

**手动编译安装（如果 Run 按钮不可用）：**

```bash
cd Service-Outsourcing/frontend/front-homo

# 编译
hvigorw assembleHap --mode module -p product=default

# 安装（HAP 路径根据实际输出调整）
hdc install empty/build/default/outputs/default/empty-default-signed.hap

# 启动应用
hdc shell aa start -a EmptyAbility -b com.example.empty
```

### 3.8 鸿蒙端功能说明

应用有 4 个页面，通过底部 TabBar 切换：

| 页面 | 功能 |
|------|------|
| 📡 监控 | ML 状态指示、WS 连接指示、图片上传检测、结果展示（状态条+OCR+缺陷网格+位置宫格）、最近记录 |
| 📋 历史 | 状态筛选 Chip、卡片式记录、分页加载 |
| 📊 统计 | 4 卡片概览、缺陷分布进度条、型号合格率 |
| ⚙️ 设置 | 产品型号管理、灵敏度/光照/曝光/分辨率参数、保存后自动重载检测器 |

### 3.9 鸿蒙端常见问题

| 问题 | 解决 |
|------|------|
| 应用打开后显示"暂无检测结果" | 正常，需要先上传图片检测。确认后端已启动且 IP 配置正确 |
| 点击"选择图片"没反应 | 开发板需要有图片。通过 `hdc file send test.jpg /data/local/tmp/` 推送，或用开发板浏览器下载图片 |
| ML 状态显示"ML离线" | 后端没加载模型。检查 `best.pt` 是否存在，调用 `curl http://后端IP:8000/api/ml/status` 确认 |
| WS 连接不上（灰色圆点） | 检查 `WebSocketClient.ets` 中的 WS_URL；确认后端用 `0.0.0.0` 启动；检查防火墙放行 8000 端口 |
| 编译报错 "Cannot find module '@ohos.net.webSocket'" | SDK 版本过低，更新到 API 10+ |
| 编译报错 "hvigorw: command not found" | 用 DevEco Studio 内置终端，或添加 PATH：`export PATH=$PATH:/path/to/deveco-studio/tools/hvigor/bin` |
| 图片上传后一直转圈 | 检查后端是否运行、IP 是否正确、后端日志是否收到请求、图片格式是否为 jpg/png |
| 开发板屏幕 UI 显示不全 | DAYU200 默认 1280×720，确认连接的是 HDMI 显示器 |

---

## 四、🏅 Web 前端部署（推荐，大屏演示）

Web 前端功能最完整（5 个页面：首页、实时监控、历史记录、统计报表、系统配置），适合电脑大屏演示和多端协同展示。

### 4.1 环境要求

| 项目 | 要求 | 验证命令 |
|------|------|----------|
| Node.js | 16+（推荐 18+） | `node --version` |
| npm | 8+ | `npm --version` |

没有 Node.js？安装：

```bash
# Linux (nvm 方式，推荐)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18

# macOS (brew)
brew install node@18

# Windows
# 下载安装包：https://nodejs.org/
```

### 4.2 方式一：开发模式（推荐开发调试时用）

```bash
cd Service-Outsourcing/frontend/web

# 安装依赖（首次执行，约 1-2 分钟）
npm install

# 启动开发服务器
npm run dev
```

浏览器打开 `http://localhost:5173`。

Vite 开发服务器会自动把 `/api`、`/static`、`/ws` 请求代理到后端 `localhost:8000`，所以**后端必须在本机运行**。

> 如果后端不在本机，需要修改 `vite.config.js` 中的 proxy target：
> ```javascript
> proxy: {
>   '/api': { target: 'http://192.168.1.100:8000' },  // ← 改成后端 IP
>   '/static': { target: 'http://192.168.1.100:8000' },
>   '/ws': { target: 'ws://192.168.1.100:8000', ws: true },
> }
> ```

### 4.3 方式二：构建生产版本（推荐演示时用）

```bash
cd Service-Outsourcing/frontend/web

# 安装依赖
npm install

# 构建（约 30 秒）
npm run build
```

构建产物在 `dist/` 目录。**后端会自动托管这些静态文件**，构建完成后直接访问 `http://后端IP:8000` 即可，不需要单独启动前端服务器。

### 4.4 功能页面一览

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `/` | 项目介绍、系统架构图、技术栈展示、功能入口 |
| 实时监控 | `/monitor` | 上传图片检测、YOLO 推理结果展示、WebSocket 实时推送、最近记录 |
| 历史记录 | `/history` | 日期/状态筛选、卡片式记录、分页、CSV 导出 |
| 统计报表 | `/statistic` | 7 天检测趋势柱状图、缺陷分布、位置分布、型号合格率 |
| 系统配置 | `/setup` | 产品型号管理、检测灵敏度、光照补偿、相机参数 |

---

## 五、💡 uni-app 移动端部署（加分项）

uni-app 是跨平台移动端框架，可以编译为 H5（手机浏览器）、微信小程序、Android/iOS App。本项目主要用 H5 模式演示，展示系统的多端覆盖能力。

### 5.1 环境要求

| 项目 | 要求 | 说明 |
|------|------|------|
| HBuilderX | 3.8+（推荐最新版） | DCloud 官方 IDE，推荐方式 |
| 或 Node.js | 16+（CLI 方式） | 不装 HBuilderX 也能跑 |

### 5.2 配置后端地址（关键步骤！）

无论用哪种方式运行，都需要先修改后端 IP。

打开 `Service-Outsourcing/frontend/front/utils/api.js`，找到 `BASE_URL`：

```javascript
// 将 localhost 改为后端实际 IP
const BASE_URL = 'http://192.168.1.100:8000'  // ← 改成你的后端 IP
```

> ⚠️ 手机浏览器访问时，`localhost` 指的是手机自己，不是你的电脑！必须改成后端的局域网 IP。
> ⚠️ 确保手机和后端在同一局域网（同一 WiFi）。

### 5.3 方式一：HBuilderX（推荐，可视化操作）

1. 下载安装 HBuilderX：https://www.dcloud.io/hbuilderx.html
2. 打开 HBuilderX → 文件 → 打开目录 → 选择 `Service-Outsourcing/frontend/front`
3. 确认已修改 `utils/api.js` 中的 `BASE_URL`
4. **运行到浏览器**：运行 → 运行到浏览器 → Chrome（H5 模式）
5. **运行到手机**：
   - USB 连接手机到电脑
   - 手机开启开发者模式和 USB 调试
   - 运行 → 运行到手机 → 选择你的设备
6. **运行到微信小程序**（可选）：
   - 需要安装微信开发者工具
   - 运行 → 运行到小程序模拟器 → 微信开发者工具

### 5.4 方式二：CLI（H5 模式，不需要 HBuilderX）

```bash
cd Service-Outsourcing/frontend/front

# 安装依赖（首次执行，约 2-3 分钟，依赖较多 ~273MB）
npm install

# 启动 H5 开发服务器
npm run dev:h5
```

启动后浏览器打开提示的地址（通常是 `http://localhost:xxxx`）。

> 手机访问：用手机浏览器打开 `http://你电脑IP:端口号`，确保在同一局域网。

### 5.5 功能页面

| 页面 | Tab 图标 | 功能 |
|------|----------|------|
| 首页 | 🏠 | ML 状态指示、图片上传检测、检测结果展示（状态条+OCR+缺陷+位置）、最近记录列表 |
| 历史 | 📋 | 状态筛选（ALL/OK/NG）、卡片式记录列表、分页加载 |
| 统计 | 📊 | 概览卡片（总数/合格/缺陷/合格率）、缺陷分布、型号合格率 |
| 设置 | ⚙️ | 产品型号管理（添加/删除/启用禁用）、灵敏度、光照补偿、相机参数 |
| 关于 | ℹ️ | 项目信息、版本号 |

### 5.6 常见问题

| 问题 | 解决 |
|------|------|
| npm install 很慢 | 使用淘宝镜像：`npm install --registry=https://registry.npmmirror.com` |
| H5 模式下图片上传没反应 | 检查 `BASE_URL` 是否正确；F12 控制台看网络请求是否 404 或 CORS 错误 |
| 手机浏览器打不开 | 确认手机和电脑在同一 WiFi；用电脑 IP 而非 localhost |
| 微信小程序编译报错 | uni-app 部分 API 在小程序中有限制，H5 模式最完整 |
| 页面样式错乱 | 清除 `node_modules` 重新安装：`rm -rf node_modules && npm install` |

---

## 六、💡 Docker 部署（加分项，适合服务器部署）

Docker 部署将后端 + Web 前端打包成一个容器，不需要在服务器上手动安装 Python/Node 环境，一条命令就能跑起来。适合在服务器上快速部署，或者给别人快速体验项目。

### 6.1 安装 Docker

**Linux（推荐）：**

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER
# 重新登录终端生效

# 安装 docker-compose（如果没有）
sudo apt install docker-compose  # Ubuntu/Debian
# 或
pip install docker-compose

# 验证
docker --version
docker-compose --version
```

**macOS / Windows：**

下载安装 Docker Desktop：https://www.docker.com/products/docker-desktop/

### 6.2 前置条件检查

```bash
# 确认 Docker 正在运行
docker info

# 确认模型权重已放好
ls yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt
# 应显示文件存在

# 确认 docker-compose.yml 存在
ls Service-Outsourcing/docker-compose.yml
```

### 6.3 构建 Web 前端（Docker 镜像需要构建产物）

```bash
cd Service-Outsourcing/frontend/web

# 安装依赖
npm install

# 构建生产版本
npm run build

# 确认构建产物
ls dist/index.html
# 应显示文件存在

cd ../..
```

### 6.4 构建并启动容器

```bash
cd Service-Outsourcing

# 构建镜像并启动（首次约 5-10 分钟，需要下载基础镜像和安装依赖）
docker-compose up -d --build

# 查看容器状态（应显示 Up）
docker-compose ps

# 查看实时日志
docker-compose logs -f
```

启动成功后日志会显示：

```
backend_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
backend_1  | INFO:ml_detection:加载Student DPFD模型...
backend_1  | INFO:inference_service:检测器初始化完成
```

### 6.5 访问

| 地址 | 说明 |
|------|------|
| `http://服务器IP:8000` | Web 前端（后端自动托管） |
| `http://服务器IP:8000/docs` | API 文档（Swagger UI） |
| `http://服务器IP:8000/api/ml/status` | ML 状态检查 |
| `ws://服务器IP:8000/ws/detection` | WebSocket 端点 |

### 6.6 日常管理

```bash
cd Service-Outsourcing

# 查看状态
docker-compose ps

# 查看日志（最近 50 行）
docker-compose logs -f --tail=50

# 重启容器
docker-compose restart

# 停止容器
docker-compose down

# 停止并删除数据卷（会清空数据库！）
docker-compose down -v

# 重新构建（代码更新后）
docker-compose up -d --build
```

### 6.7 Docker 常见问题

| 问题 | 解决 |
|------|------|
| `docker-compose up` 报错 "port already in use" | 端口 8000 被占用，先停掉占用进程：`lsof -i :8000` 然后 `kill -9 PID` |
| 构建时下载基础镜像很慢 | 配置 Docker 镜像加速器（阿里云/腾讯云） |
| 容器启动后 ML 状态 unavailable | 检查模型权重是否在 `docker-compose.yml` 的 volumes 映射路径中 |
| 容器内存不足 | Docker Desktop 默认内存 2GB，建议调到 4GB+（Settings → Resources） |
| `npm run build` 失败 | 确认 Node.js 版本 16+；清除缓存 `rm -rf node_modules && npm install` |

---

## 七、多端协同演示流程（比赛用）

```
步骤 1：启动后端
  conda activate yolo_distiller_lmc
  cd Service-Outsourcing/backend
  uvicorn main:app --host 0.0.0.0 --port 8000

步骤 2：打开 Web 端
  浏览器访问 http://后端IP:8000（需要先 npm run build）
  或开发模式 http://localhost:5173

步骤 3：打开鸿蒙端
  开发板上启动应用（确保 IP 已配置正确）

步骤 4：演示检测
  在 Web 端 /monitor 页面上传能效标签图片
  → YOLO 推理 + OCR 识别 → 综合判定（OK/NG）
  → 鸿蒙端通过 WebSocket 实时收到结果，自动更新 UI
  → 展示缺陷检测（5 种类型）和位置检测（3×3 宫格）

步骤 5：演示历史和统计
  切换到 /history 页面，展示筛选和 CSV 导出
  切换到 /statistic 页面，展示 7 天趋势和缺陷分布

步骤 6：演示配置热更新
  切换到 /setup 页面，调整灵敏度为"高"
  保存 → 自动重载检测器 → 再次检测，对比结果差异
```

---

## 八、环境变量说明

后端支持通过环境变量或 `.env` 文件配置（`.env` 文件放在 `Service-Outsourcing/backend/` 目录下）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8000` | 允许的跨域源，逗号分隔。设为 `*` 时自动关闭 credentials |
| `DATABASE_URL` | `sqlite:///backend/detection.db` | 数据库连接字符串，支持 PostgreSQL 等 |

`.env` 文件示例见 `Service-Outsourcing/backend/.env.example`。

---

## 九、故障排查大全

### 后端启动失败

```bash
# 检查是否在正确的 conda 环境
conda activate yolo_distiller_lmc
which python  # 应指向 conda 环境

# 检查端口是否被占用
lsof -i :8000
# 如果被占用，杀掉进程：kill -9 <PID>

# 检查依赖是否安装完整
python -c "import fastapi, sqlalchemy, pydantic, torch, ultralytics; print('OK')"

# 查看详细错误
uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | head -50
```

### 模型加载失败

```bash
# 检查模型文件是否存在
ls -la yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt
# 应显示文件大小约 5.3MB

# 如果文件不存在，检查路径是否正确
find yolo-distiller/runs -name "best.pt"

# 检查 ML 状态 API
curl http://localhost:8000/api/ml/status
```

### 前端连不上后端

```bash
# 检查后端是否在运行
curl http://后端IP:8000/api/config
# 如果超时或拒绝连接，后端没启动或 IP 不对

# 检查防火墙
sudo ufw status
sudo ufw allow 8000

# 浏览器 F12 控制台看 CORS 错误
# 如果有 CORS 错误，检查 CORS_ORIGINS 环境变量是否包含前端地址
```

### 开发板连不上

```bash
# 检查 USB 连接
hdc list targets
# 应输出设备序列号

# 重启 hdc 服务
hdc kill
hdc list targets

# WiFi 调试时检查网络
hdc shell ifconfig
ping 开发板IP
```

### 数据库问题

```bash
# 查看数据库文件
ls -la Service-Outsourcing/backend/detection.db

# 用 sqlite3 查看数据
sqlite3 Service-Outsourcing/backend/detection.db "SELECT COUNT(*) FROM detection_records;"

# 重置数据库（删除后重启后端会自动重建）
rm Service-Outsourcing/backend/detection.db
```

---

## 十、生产部署注意事项

| 项目 | 开发环境 | 生产环境 |
|------|----------|----------|
| 后端地址 | `http://192.168.x.x:8000` | 改为域名或公网 IP |
| WebSocket | `ws://192.168.x.x:8000/ws/detection` | 改为 `wss://`（HTTPS） |
| 签名 | 调试签名（DevEco 自动） | 需要正式签名证书 |
| 模型推理 | CPU（~100ms） | GPU 推理更快（~20ms） |
| 数据库 | SQLite 单文件 | 可迁移到 PostgreSQL |
| 反向代理 | 无 | 建议 Nginx + HTTPS |
