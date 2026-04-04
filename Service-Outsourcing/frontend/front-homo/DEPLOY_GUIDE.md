# 鸿蒙端部署指南（DAYU200 RK3568）

本文档面向拿到开发板的同学，从 GitHub 拉取代码后，按步骤完成鸿蒙端应用的编译和部署。

---

## 前置条件

- DAYU200 (HH-SCDAYU200) 开发板，已刷入 OpenHarmony 4.0+ 系统
- Windows/macOS 电脑，已安装 DevEco Studio 4.0+
- USB 数据线连接开发板
- 开发板和后端服务器在同一局域网

---

## 第一步：拉取代码

```bash
git clone https://github.com/你的用户名/LMC.git
cd LMC/Service-Outsourcing/frontend/front-homo
```

---

## 第二步：安装 DevEco Studio

1. 下载地址：https://developer.huawei.com/consumer/cn/deveco-studio/
2. 安装后打开，首次启动会提示安装 OpenHarmony SDK，选择 API 10 或以上
3. 确认 Node.js 和 ohpm 已自动配置

---

## 第三步：打开项目

1. DevEco Studio → File → Open → 选择 `LMC/Service-Outsourcing/frontend/front-homo` 目录
2. 等待 Sync 完成（首次会下载依赖，可能需要几分钟）
3. 如果提示 SDK 版本不匹配，按提示更新

---

## 第四步：修改后端地址

打开文件 `empty/src/main/ets/common/Api.ets`，修改第 4 行：

```typescript
// 改为后端服务器的实际局域网 IP
const BASE_URL: string = 'http://192.168.x.x:8000';
```

查找后端 IP 的方法：
- 在运行后端的电脑上执行 `ip addr` (Linux) 或 `ipconfig` (Windows)
- 找到局域网 IP（通常是 192.168.x.x 或 10.x.x.x）

---

## 第五步：连接开发板

1. USB 连接 DAYU200 到电脑
2. 打开终端，验证连接：
   ```bash
   hdc list targets
   ```
   应该显示设备序列号，如 `7001005458323933328a...`
3. 如果没有识别到设备：
   - 检查 USB 线是否支持数据传输（不是仅充电线）
   - Windows 需要安装 HDC 驱动
   - 确认开发板已开机且屏幕亮起

---

## 第六步：编译部署

1. DevEco Studio 顶部工具栏，选择目标设备（应显示你的 DAYU200）
2. 选择 `empty` 模块
3. 点击 ▶ Run 按钮（或 Shift+F10）
4. 等待编译完成，应用会自动安装到开发板并启动

首次编译可能需要 2-3 分钟，后续增量编译很快。

---

## 第七步：启动后端

在后端服务器上（需要和开发板同一局域网）：

```bash
cd LMC/Service-Outsourcing/backend
pip install -r requirements.txt
pip install -r requirements-ml.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

注意：
- `--host 0.0.0.0` 是必须的，否则开发板无法访问
- 模型权重文件（*.pt）不在 GitHub 仓库中，需要单独获取：
  - 方式一：从团队共享网盘下载，放到 `LMC/yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt`
  - 方式二：自行训练（参考 DEV_DOC.md 阶段一）
  - 方式三：不放模型，后端仍可启动，但 ML 检测功能不可用（其他 API 正常）

---

## 功能说明

应用有 4 个页面，通过底部 TabBar 切换：

| 页面 | 功能 |
|------|------|
| 📡 监控 | 实时检测结果展示、图片上传检测、WebSocket 实时推送 |
| 📋 历史 | 历史检测记录、状态筛选、分页加载 |
| 📊 统计 | 检测总览、缺陷分布、型号合格率 |
| ⚙️ 设置 | 预设型号管理、灵敏度/容忍度/光照补偿参数配置 |

---

## 常见问题

**Q: 应用打开后显示"暂无检测结果"**
A: 正常，需要先通过 Web 端或应用内上传图片检测。确认后端已启动且 IP 地址正确。

**Q: 点击"选择图片"没反应**
A: 开发板需要有图片文件。可以先通过 hdc 推送测试图片：
```bash
hdc file send test_image.jpg /data/local/tmp/
```

**Q: ML 状态显示"ML离线"**
A: 后端没有加载模型权重。检查 `yolo-distiller/runs/` 下是否有 `best.pt` 文件。

**Q: WebSocket 连接不上（WS 指示灯灰色）**
A: 检查防火墙是否放行 8000 端口，确认后端 `--host 0.0.0.0` 启动。

**Q: 编译报错 "Cannot find module '@ohos.net.webSocket'"**
A: SDK 版本过低，需要 API 9+。在 DevEco Studio 中更新 OpenHarmony SDK。

---

## 文件结构

```
front-homo/
├── empty/src/main/ets/
│   ├── common/
│   │   ├── Api.ets              ← 修改这里的 BASE_URL
│   │   └── WebSocketClient.ets  ← WebSocket 封装
│   ├── pages/
│   │   ├── Index.ets            ← 监控页（主页+TabBar）
│   │   ├── History.ets          ← 历史记录
│   │   ├── Statistics.ets       ← 数据统计
│   │   └── Settings.ets         ← 系统设置
│   └── emptyability/
│       └── EmptyAbility.ets     ← 应用入口
├── empty/src/main/resources/
│   └── base/profile/
│       └── main_pages.json      ← 页面路由注册
└── DEPLOY_GUIDE.md              ← 本文档