# OpenHarmony 鸿蒙端部署指南

> 目标设备：DAYU200 (RK3568) · OpenHarmony 4.0+
> 开发工具：DevEco Studio 4.0+ (API 10)

本文档面向拿到开发板的同学，从 GitHub 拉取代码后，按步骤完成鸿蒙端应用的编译、部署和联调。

---

## 一、环境准备

### 1.1 硬件

| 设备 | 要求 |
|------|------|
| 开发板 | DAYU200 (HH-SCDAYU200)，已刷入 OpenHarmony 4.0+ 系统镜像 |
| 电脑 | Windows 10/11 或 macOS 12+，8GB+ 内存 |
| USB 线 | 支持数据传输的 USB-A to USB-C 线（不能是仅充电线） |
| 网络 | 开发板和后端服务器在同一局域网（WiFi 或有线） |

### 1.2 软件

| 软件 | 版本 | 说明 |
|------|------|------|
| DevEco Studio | 4.0+ | 华为官方 IDE，下载地址见下方 |
| OpenHarmony SDK | API 10+ | DevEco Studio 首次启动时自动安装 |
| Node.js | 16+ | DevEco Studio 自带，无需单独安装 |
| ohpm | 自带 | OpenHarmony 包管理器，DevEco Studio 自带 |
| hdc | 自带 | 设备调试工具，DevEco Studio 自带 |

### 1.3 安装 DevEco Studio

1. 下载地址：https://developer.huawei.com/consumer/cn/deveco-studio/
2. 安装后首次启动，按向导完成：
   - 选择 OpenHarmony 开发模式（不是 HarmonyOS）
   - 安装 OpenHarmony SDK，选择 API 10 或以上
   - 等待 Node.js、ohpm 自动配置完成
3. 验证安装：File → Settings → OpenHarmony SDK，确认 SDK 路径和版本号

---

## 二、拉取代码

```bash
git clone https://github.com/Stardep-lmc/EnergyLabel-Detection-System.git
cd EnergyLabel-Detection-System
```

鸿蒙端代码位于：

```
Service-Outsourcing/frontend/front-homo/
├── empty/src/main/ets/
│   ├── common/
│   │   ├── Api.ets              ← API 封装层（需修改 BASE_URL）
│   │   └── WebSocketClient.ets  ← WebSocket 封装（需修改 WS_URL）
│   ├── pages/
│   │   ├── Index.ets            ← 监控页（主页 + 底部 TabBar）
│   │   ├── History.ets          ← 历史记录页
│   │   ├── Statistics.ets       ← 数据统计页
│   │   └── Settings.ets         ← 系统设置页
│   └── emptyability/
│       └── EmptyAbility.ets     ← 应用入口 Ability
├── empty/src/main/resources/
│   └── base/profile/
│       └── main_pages.json      ← 页面路由注册（4 个页面）
├── empty/build-profile.json5    ← 构建配置
├── oh-package.json5             ← 项目依赖
└── DEPLOY_GUIDE.md              ← 本文档
```

---

## 三、打开项目

1. 启动 DevEco Studio
2. File → Open → 选择 `Service-Outsourcing/frontend/front-homo` 目录
3. 等待 Sync 完成（首次会下载依赖，约 2-5 分钟）
4. 如果提示 SDK 版本不匹配，按提示更新 SDK
5. 如果 ohpm install 失败，检查网络连接，或手动执行：
   ```bash
   cd Service-Outsourcing/frontend/front-homo
   ohpm install
   ```

---

## 四、配置后端地址（关键步骤）

### 4.1 查找后端 IP

在运行后端的电脑上执行：

```bash
# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1

# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

找到局域网 IP，通常是 `192.168.x.x` 或 `10.x.x.x`。

### 4.2 修改 API 地址

打开 `empty/src/main/ets/common/Api.ets`，修改第 4 行：

```typescript
// 将 localhost 改为后端实际 IP
const BASE_URL: string = 'http://192.168.1.100:8000';  // ← 改成你的 IP
```

### 4.3 修改 WebSocket 地址

打开 `empty/src/main/ets/common/WebSocketClient.ets`，找到 WS URL 配置：

```typescript
// 将 localhost 改为后端实际 IP
const WS_URL: string = 'ws://192.168.1.100:8000/ws/detection';  // ← 改成你的 IP
```

> 注意：两个文件的 IP 必须一致，且后端必须以 `--host 0.0.0.0` 启动才能被开发板访问。

---

## 五、启动后端服务

在后端服务器上（需要和开发板同一局域网）：

```bash
cd EnergyLabel-Detection-System/Service-Outsourcing/backend

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-ml.txt  # ML 检测功能（YOLO + PaddleOCR）

# 启动（必须 0.0.0.0，否则开发板无法访问）
uvicorn main:app --host 0.0.0.0 --port 8000
```

验证后端可访问：

```bash
# 在后端机器上
curl http://localhost:8000/api/config

# 在开发板同一局域网的其他设备上
curl http://192.168.1.100:8000/api/config
```

### 模型权重文件

模型权重（`*.pt`）不在 Git 仓库中（文件太大），需要单独获取：

| 方式 | 说明 |
|------|------|
| 团队网盘 | 从共享网盘下载 `best.pt`，放到 `yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt` |
| 自行训练 | 参考 `DEV_DOC.md` 阶段一，约需 GPU 16 小时 |
| 不放模型 | 后端仍可启动，API 正常，但 `/api/ml/detect` 返回 503 |

---

## 六、连接开发板

### 6.1 USB 连接

1. USB 线连接 DAYU200 到电脑
2. 确认开发板已开机（屏幕亮起）
3. 打开终端验证：

```bash
hdc list targets
```

应输出设备序列号，如 `7001005458323933328a01e4e3825800`。

### 6.2 连接失败排查

| 问题 | 解决方案 |
|------|----------|
| `[Empty]` 无设备 | 检查 USB 线是否支持数据传输；换 USB 口试试 |
| Windows 无法识别 | 安装 HDC USB 驱动：DevEco Studio → Tools → Device Manager → Install Driver |
| macOS 无法识别 | 系统偏好设置 → 安全性与隐私 → 允许 HDC 访问 |
| 设备离线 | 重启开发板；重新插拔 USB；执行 `hdc kill` 后重试 |

### 6.3 WiFi 调试（可选）

如果不想一直插 USB 线：

```bash
# 先通过 USB 连接，获取开发板 IP
hdc shell ifconfig

# 开启 TCP 调试（端口 5555）
hdc tconn 192.168.1.200:5555

# 之后可以拔掉 USB，通过 WiFi 调试
hdc list targets  # 应显示 IP:5555
```

---

## 七、编译部署

1. DevEco Studio 顶部工具栏，选择目标设备（应显示你的 DAYU200）
2. 选择 `empty` 模块
3. 点击 ▶ Run 按钮（或 Shift+F10）
4. 等待编译完成，应用会自动安装到开发板并启动

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 首次编译 | 2-3 分钟 | 需要编译所有模块 |
| 增量编译 | 10-30 秒 | 只编译修改的文件 |
| 安装到设备 | 5-10 秒 | 通过 hdc 推送 HAP 包 |

### 手动安装（可选）

如果 Run 按钮不可用，可以手动编译安装：

```bash
# 编译
cd Service-Outsourcing/frontend/front-homo
hvigorw assembleHap --mode module -p product=default

# 安装（HAP 路径根据实际输出调整）
hdc install empty/build/default/outputs/default/empty-default-signed.hap

# 启动应用
hdc shell aa start -a EmptyAbility -b com.example.empty
```

---

## 八、功能说明

应用有 4 个页面，通过底部 TabBar 切换：

### 📡 监控页（Index）

- ML 服务状态指示器（绿色在线/红色离线）
- WebSocket 实时推送指示器（绿色已连接/灰色断开）
- 图片上传检测：点击"选择图片"→ 从相册选取 → 上传到后端 → 显示检测结果
- 检测结果展示：
  - 状态条（OK 绿色 / NG 红色）
  - 标签识别（OCR 文本 + 置信度）
  - 缺陷检测（5 种类型网格：正常/偏移/划痕/污渍/褶皱）
  - 位置检测（3×3 宫格可视化）
- 最近检测记录表格（自动刷新）

### 📋 历史页（History）

- 状态筛选 Chip（全部/合格/不合格）
- 卡片式记录展示（型号 + 缺陷 + 位置 + 时间）
- 分页加载更多
- 返回导航

### 📊 统计页（Statistics）

- 4 卡片概览（总检测数、合格数、不合格数、合格率）
- 缺陷分布进度条（各缺陷类型占比，颜色分级）
- 型号合格率进度条

### ⚙️ 设置页（Settings）

- 预设产品型号管理（添加/删除/启用禁用 Toggle）
- 检测参数：
  - 位置偏移容忍度（滑块 0-20%）
  - 缺陷检测灵敏度（低/中/高 三档）
  - 光照补偿（-5 ~ +5）
- 相机参数：曝光（-3 ~ +3）、分辨率选择
- 保存配置后自动重载 ML 检测器（灵敏度等参数立即生效）

---

## 九、WebSocket 实时推送

应用内置 WebSocket 客户端，连接后端 `/ws/detection` 端点：

- 自动连接：应用启动时自动连接
- 心跳保活：每 30 秒发送 ping，服务端回 pong
- 断线重连：连接断开后自动重连（间隔 3 秒，最多 10 次）
- 状态指示：监控页顶部显示 WS 连接状态（绿色/灰色圆点）
- 实时更新：Web 端或其他客户端检测后，结果自动推送到鸿蒙端

---

## 十、常见问题

### Q: 应用打开后显示"暂无检测结果"
正常现象。需要先通过应用内上传图片检测，或通过 Web 端检测。确认后端已启动且 IP 地址配置正确。

### Q: 点击"选择图片"没反应
开发板需要有图片文件。通过 hdc 推送测试图片：
```bash
hdc file send test_image.jpg /data/local/tmp/
```
或者通过开发板浏览器下载图片到相册。

### Q: ML 状态显示"ML离线"
后端没有加载模型权重。检查：
1. `yolo-distiller/runs/` 下是否有 `best.pt` 文件
2. 后端启动日志是否显示 "Model loaded"
3. 调用 `curl http://后端IP:8000/api/ml/status` 确认

### Q: WebSocket 连接不上（WS 指示灯灰色）
1. 检查 `WebSocketClient.ets` 中的 WS_URL 是否正确
2. 确认后端以 `--host 0.0.0.0` 启动
3. 检查防火墙是否放行 8000 端口：
   ```bash
   # Linux
   sudo ufw allow 8000
   # 或
   sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
   ```

### Q: 编译报错 "Cannot find module '@ohos.net.webSocket'"
SDK 版本过低。在 DevEco Studio 中：File → Settings → OpenHarmony SDK → 更新到 API 10+。

### Q: 编译报错 "hvigorw: command not found"
DevEco Studio 的构建工具未加入 PATH。使用 DevEco Studio 内置终端，或手动添加：
```bash
export PATH=$PATH:/path/to/deveco-studio/tools/hvigor/bin
```

### Q: 图片上传后一直转圈
1. 检查后端是否正常运行
2. 检查 `Api.ets` 中的 BASE_URL 是否正确
3. 查看后端日志是否收到请求
4. 确认图片格式为 jpg/jpeg/png

### Q: 开发板屏幕太小，UI 显示不全
DAYU200 默认分辨率 1280×720。应用 UI 已适配该分辨率。如果显示异常：
1. 检查开发板显示设置
2. 确认连接的是 HDMI 显示器而非 MIPI 屏

---

## 十一、多端协同演示

系统支持 Web + uni-app + 鸿蒙三端协同：

1. 启动后端：`uvicorn main:app --host 0.0.0.0 --port 8000`
2. 打开 Web 端：浏览器访问 `http://后端IP:8000`
3. 打开鸿蒙端：开发板上启动应用
4. 在 Web 端上传图片检测
5. 鸿蒙端通过 WebSocket 实时收到检测结果，自动更新 UI

这个流程可以用于比赛演示，展示多端实时协同能力。

---

## 十二、生产部署注意事项

| 项目 | 开发环境 | 生产环境 |
|------|----------|----------|
| 后端地址 | `http://192.168.x.x:8000` | 改为域名或公网 IP |
| WebSocket | `ws://192.168.x.x:8000/ws/detection` | 改为 `wss://` (HTTPS) |
| 签名 | 调试签名（DevEco 自动） | 需要正式签名证书 |
| 模型 | CPU 推理 (~84ms) | GPU 推理更快 |
| 数据库 | SQLite 单文件 | 可迁移到 PostgreSQL |