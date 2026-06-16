# 🖥️ SignBoard 数字标牌系统

> 基于 Python 的开源内网数字信息发布系统，支持 Windows + Android 多平台统一管理与播放。

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2B%20%7C%20Android_7.0%2B-lightgrey)
![Version](https://img.shields.io/badge/Version-2.1-orange)

---

## 📖 简介

SignBoard 是一个轻量级数字标牌系统，专为局域网环境设计。由三部分组成：

- **CMS Server**：内容管理服务端，提供 Web 管理后台和 REST API
- **Windows Player**：Windows 全屏播放器，自动拉取内容并播放
- **Android Player**：Android 全屏播放器，支持熄屏/唤醒/重启控制

无需互联网连接，无需安装数据库，单 EXE/APK 部署即可运行。

### 核心功能

| 功能 | 说明 |
|---|---|
| 📤 素材管理 | 图片(JPG/PNG/GIF/WebP)、视频(MP4/WebM/MKV)、PPT(自动转图 + 多页轮播)、**标签分组、分辨率自动检测、过期清理** |
| 🎨 布局设计 | 全屏轮播、播放列表、**网页组件**、左右二分屏、上中下三分屏(含走马灯)，**三栏编辑器** |
| 📐 分辨率适配 | 布局绑定分辨率（1920×1080 横屏 / 1080×1920 竖屏 / 自定义），横竖屏独立配置，**快捷按钮** |
| 📅 排程管理 | 按时间、屏幕、优先级调度，支持重复排程（每天/每周/每月，含跨天时段） |
| 🚨 紧急插播 | 最高优先级排程，立即覆盖当前播放内容，SSE 实时推送到 Player |
| 🖥️ 屏幕管理 | 在线/离线状态检测、实时截图、远程重启、**设备分组、批量操作、绑定信息显示** |
| 📡 SSE 实时推送 | Server 通过 SSE 长连接即时推送指令和紧急插播，30 秒轮询兜底 |
| 🔄 自动同步 | 30秒拉取排程，素材增量下载，失败自动重试 |
| 📡 离线播放 | 服务器离线时自动播放上次缓存的内容，恢复后自动同步 |
| 📸 远程截图 | 60秒自动 + 手动触发，仪表盘实时预览 |
| 🎵 音频控制 | 视频音轨 + 独立背景音乐，音量分开调节 |
| ✨ 过渡动画 | 淡入淡出，时长可配 |
| 🖼️ 填充模式 | 裁切填满(无黑边) / 保持比例(有黑边) / 拉伸填满 |
| 🔐 多用户权限 | 管理员/操作员/只读，操作日志审计，**用户管理页面** |
| 🔑 修改密码 | 修改密码自动踢掉所有其他设备的登录 |
| 👁️ 素材预览 | 点击素材查看原图、播放视频、PPT 多页翻页预览，**布局绑定素材可点击预览** |
| 🏷️ 素材标签 | 标签分组筛选、批量打标签/取消标签，**标签管理页面** |
| 📊 PPT 播放 | 支持轮播全部页（每页时长可配）或固定显示某一页 |
| 📱 远程控制 | 远程熄屏/唤醒/重启（二次确认），**支持批量操作** |
| ⏰ 开关机计划 | 按设备/全部设备绑定，自定义执行日和时间，Server 自动调度 |
| 📋 下发记录 | 所有命令下发记录（手动+自动），支持筛选和分页 |
| 📦 设备分组 | 按区域/用途分组管理设备，支持分组筛选、搜索、状态过滤 |

### 4 种布局模板

```
┌──────────────────┐  ┌──────────────────┐  ┌────────┬─────────┐  ┌──────────────────┐
│                  │  │  ① 素材A (30s)    │  │        │         │  │  ① 视频/图片      │
│   全屏轮播       │  │  ② 素材B (15s)    │  │  图片  │  视频   │  │──────────────────│
│   (统一时长)     │  │  ③ 素材C (20s)    │  │        │         │  │  ② 图片           │
│                  │  │  ...              │  │ 1:1/16:9        │  │──────────────────│
│                  │  │                   │  │        │         │  │  ③ 走马灯文字     │
└──────────────────┘  └──────────────────┘  └────────┴─────────┘  └──────────────────┘
   fullscreen             playlist              split_2              split_3
```

---

## 🏗️ 项目结构

```
signboard/
├── server/                    # CMS 服务端
│   ├── main.py                # 入口（FastAPI + PyQt6 状态窗口 + 鉴权中间件）
│   ├── models.py              # SQLAlchemy ORM 模型 + 数据库迁移
│   ├── ppt_converter.py       # PPTX → JPG 转换器（LibreOffice + python-pptx fallback）
│   ├── status_window.py       # 本地状态窗口（PyQt6）
│   ├── api/
│   │   ├── media.py           # 素材 CRUD + 上传/缩略图/PPT 转换
│   │   ├── layout.py          # 布局 CRUD + 引用校验
│   │   ├── schedule.py        # 排程 CRUD + 重复排程 + 紧急插播 SSE 通知
│   │   ├── display.py         # 屏幕注册/心跳/指令/截图
│   │   ├── player_sync.py     # Player 同步 + SSE 推送 + 素材下载
│   │   └── auth.py            # 登录/登出/修改密码
│   └── templates/admin/
│       ├── index.html         # Web 管理后台入口
│       └── assets/            # Vite 构建产物（JS/CSS）
├── player/                    # Windows 播放器
│   ├── main.py                # 入口（命令行参数 + 配置对话框 + 离线恢复）
│   ├── player_window.py       # 全屏播放主窗口 + 布局切换 + 离线指示
│   ├── renderer.py            # 渲染引擎（图片 3 种填充模式 / 视频 / 走马灯）
│   ├── sync.py                # SSE 实时监听 + 轮询同步 + 心跳 + 截图 + 离线缓存
│   ├── audio.py               # 音频管理（BGM + 音量）
│   ├── remote_control.py      # 远程控制（熄屏/唤醒/重启）
│   └── layouts/
│       ├── base.py            # 布局基类
│       ├── fullscreen.py      # 全屏轮播布局
│       ├── playlist.py        # 播放列表布局
│       ├── split_2.py         # 左右二分屏布局（百分比定位）
│       └── split_3.py         # 上中下三分屏布局
├── frontend/                  # Vue 3 前端源码
│   ├── src/
│   │   ├── views/             # 页面组件（Dashboard/Media/Layouts/Schedules/Displays）
│   │   ├── components/        # 通用组件（Toast 通知）
│   │   ├── api/               # API 层（axios 封装）
│   │   ├── stores/            # Pinia 状态管理
│   │   └── router/            # Vue Router（hash 模式）
│   ├── vite.config.js         # Vite 配置
│   └── package.json
├── android-player/            # Android 播放器
│   ├── app/src/main/
│   │   ├── java/com/signboard/player/
│   │   │   ├── MainActivity.kt      # 配置界面
│   │   │   ├── PlayerActivity.kt    # 播放界面
│   │   │   ├── service/PlayerService.kt  # 前台 Service + 看门狗
│   │   │   ├── sync/                # 同步模块（SSE + 轮询）
│   │   │   ├── player/              # 播放模块（图片/视频/走马灯）
│   │   │   ├── control/RemoteControl.kt  # 远程控制（熄屏/唤醒/重启）
│   │   │   └── api/                 # API 接口
│   │   └── AndroidManifest.xml
│   ├── build.gradle.kts
│   └── README.md
├── shared/                    # 共享模块
│   ├── config.py              # 全局配置
│   ├── schemas.py             # Pydantic 数据模型
│   ├── time_utils.py          # 时区工具
│   └── logging_config.py      # 日志配置
├── docs/
│   ├── 开发记录.md             # 开发过程记录
│   └── Android端开发方案.md    # Android 端开发方案
├── build_common.py            # 构建共享模块（DLL 收集逻辑）
├── build_server.py            # Server EXE 打包脚本
├── build_player.py            # Player EXE 打包脚本
├── requirements-server.txt    # Server 依赖
├── requirements-player.txt    # Player 依赖
└── README.md                  # 本文件
```

---

## 🚀 快速开始

### 环境要求

- Windows 10 或更高版本（Server + Windows Player）
- Android 7.0+（Android Player）
- 内网网络互通（无需互联网）

### 方式一：EXE/APK 部署（推荐生产环境）

```bash
# 打包（在开发机上执行）
python build_server.py    # 生成 dist/signboard-server/
python build_player.py    # 生成 dist/signboard-player/
# Android Player：用 Android Studio 打开 android-player/ 目录，Build APK

# 部署
# Server：复制 dist/signboard-server/ 整个文件夹到服务器，双击 signboard-server.exe
# Windows Player：复制 dist/signboard-player/ 整个文件夹到各屏幕终端，双击 signboard-player.exe
# Android Player：将 app-debug.apk 安装到 Android 设备
```

首次启动 Player 时弹出配置窗口输入服务器地址，之后自动启动不再弹窗。

**默认登录：** 首次启动时 Server 控制台会打印随机生成的管理员密码，请及时登录并修改。如需重置：`signboard-server.exe --reset-password admin`

#### 外置模板（改前端不用重新打包）

Server 打包后支持将前端文件放在 exe 同级目录，修改后刷新浏览器即生效：

```
dist/signboard-server/
├── signboard-server.exe
├── server/templates/admin/
│   ├── index.html              ← 外置模板入口
│   └── assets/                 ← Vite 构建产物（JS/CSS）
├── data/signboard.db
└── uploads/
```

如果外置目录不存在，自动 fallback 到 exe 内嵌版本。

### 方式二：源码运行

```bash
# 1. 安装依赖
pip install -r requirements-server.txt
pip install -r requirements-player.txt

# 2. 启动服务端
python -m server.main --port 8000

# 3. 启动播放器（另一台电脑或同机测试）
python -m player.main --server 192.168.1.100:8000
```

#### 前端开发（可选）

```bash
cd frontend
npm install
npm run dev          # 开发模式（热更新，代理到 localhost:8000）
npm run build        # 构建产物输出到 server/templates/admin/
```

---

## 📋 使用指南

### 1. 启动 Server

```
双击 signboard-server.exe
→ 自动弹出状态窗口（端口、IP、在线屏幕数）
→ 自动打开浏览器到管理后台
```

命令行选项：

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--port` | 监听端口 | 8000 |
| `--host` | 监听地址 | 0.0.0.0 |
| `--no-browser` | 不自动打开浏览器 | false |
| `--no-gui` | 纯控制台模式（不显示状态窗口） | false |
| `--reset-password` | 重置指定用户密码 | - |

### 2. 使用管理后台

浏览器访问 `http://<服务器IP>:8000`

#### 素材管理
1. 点击「上传素材」
2. 支持批量选择图片、视频、PPT 文件
3. PPT 文件上传后自动转换为图片序列
4. 可按类型筛选、双击改名、删除素材（自动检查引用关系）

#### 布局设计
1. 点击「新建布局」
2. 选择分辨率（1920×1080 横屏 / 1080×1920 竖屏 / 3840×2160 4K / 自定义）
3. 选择布局模板（全屏/列表/二分屏/三分屏）
4. 为每个区域选择素材，配置时长、音量、填充模式
5. 三分屏还需配置走马灯文字/颜色/速度

#### 排程管理
1. 点击「新建排程」
2. 选择布局 + 目标屏幕（不选=全部屏幕）
3. 设置开始/结束时间（结束时间留空=永久）
4. 设置优先级（数字越大越优先）
5. 可选重复排程：每天/每周/每月，支持跨天时段（如 22:00-06:00）
6. 日历视图可按月查看排程分布，支持紧急插播

#### 屏幕管理
- 查看所有屏幕在线状态（自动检测离线，超时 2 分钟）
- 查看屏幕分辨率（Player 自动上报）
- 📸 即时截图：远程触发屏幕抓取当前画面
- 🔄 远程重启：下发系统重启指令（10秒延迟）

### 3. 部署 Player

```bash
# 直接双击（首次弹窗配置，之后自动启动）
signboard-player.exe

# 命令行指定服务器
signboard-player.exe --server 192.168.1.100:8000

# 指定屏幕名称
signboard-player.exe --server 192.168.1.100:8000 --name "一楼大厅"

# 强制重新配置
signboard-player.exe --config
```

Player 启动后：
- 自动全屏（无边框 + 隐藏鼠标）
- 按 **Esc** 退出
- SSE 实时接收 Server 推送 + 30 秒轮询兜底
- 每 60 秒自动截图上传
- 服务器离线时自动播放上次缓存的内容，角落显示「⚠ 离线模式」提示
- 服务器恢复后自动切回在线模式

### 4. 开机自启

将 Player 快捷方式放入 Windows 启动文件夹：

```
按 Win+R → 输入 shell:startup → 回车
→ 创建快捷方式 → 目标填写：
  signboard-player.exe
```

（首次配置后会自动保存，后续启动无需参数）

---

## 🔧 技术栈

| 组件 | 技术 | 说明 |
|---|---|---|
| 后端框架 | FastAPI 0.115+ | 异步高性能 REST API |
| ORM | SQLAlchemy 2.0+ | 数据库抽象层 + 自动迁移 |
| 数据库 | SQLite 3 | 嵌入式文件数据库，零运维 |
| Windows 播放器 | PyQt6 + Qt Multimedia | 原生 Windows 全屏渲染 |
| Android 播放器 | Kotlin + ExoPlayer + Coil | Android 原生全屏渲染 |
| PPT 转换 | LibreOffice + python-pptx | 双级 fallback 策略 |
| 前端框架 | Vue 3 + Vite + Pinia + Vue Router | SPA 架构，hash 模式路由 |
| UI 样式 | Tailwind CSS v4 | 原子化 CSS |
| 图标库 | Lucide Vue Next | 轻量矢量图标 |
| 实时推送 | SSE (Server-Sent Events) | Server → Player 即时通知 |
| 打包 | PyInstaller | onedir 模式 |
| HTTP 客户端 | httpx + requests | Player 端网络请求 |

---

## 🌐 API 概览

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| POST | `/api/v1/auth/login` | 登录 | ✕ |
| POST | `/api/v1/auth/logout` | 登出 | ✓ |
| GET | `/api/v1/auth/me` | 检查登录状态 | ✓ |
| POST | `/api/v1/auth/change-password` | 修改密码（踢掉其他设备） | ✓ |
| POST | `/api/v1/media/upload` | 上传素材 | ✓ |
| GET | `/api/v1/media/list` | 素材列表 | ✓ |
| PUT | `/api/v1/media/{id}` | 更新素材名称 | ✓ |
| DELETE | `/api/v1/media/{id}` | 删除素材（自动检查引用） | ✓ |
| POST | `/api/v1/layouts` | 创建布局 | ✓ |
| GET | `/api/v1/layouts/list` | 布局列表 | ✓ |
| PUT | `/api/v1/layouts/{id}` | 更新布局 | ✓ |
| DELETE | `/api/v1/layouts/{id}` | 删除布局（自动检查排程引用） | ✓ |
| POST | `/api/v1/schedules` | 创建排程 | ✓ |
| GET | `/api/v1/schedules/list` | 排程列表 | ✓ |
| PATCH | `/api/v1/schedules/{id}` | 部分更新排程（暂停/启用等） | ✓ |
| PUT | `/api/v1/schedules/{id}` | 更新排程 | ✓ |
| DELETE | `/api/v1/schedules/{id}` | 删除排程 | ✓ |
| POST | `/api/v1/displays/register` | 屏幕注册 | ✕ |
| GET | `/api/v1/displays/list` | 屏幕列表（支持分组/状态/搜索筛选） | ✓ |
| POST | `/api/v1/displays/command` | 下发指令 | ✓ |
| POST | `/api/v1/displays/{id}/screenshot` | 上传截图 | ✕ |
| GET | `/api/v1/displays/{id}/screenshot` | 获取截图 | ✓ |
| PUT | `/api/v1/displays/batch/group` | 批量设置设备分组 | ✓ |
| PUT | `/api/v1/displays/batch/layout` | 批量绑定布局 | ✓ |
| POST | `/api/v1/displays/{id}/heartbeat` | Player 心跳上报（含平台/IP/分辨率） | ✕ |
| GET | `/api/v1/device-groups` | 设备分组列表 | ✓ |
| POST | `/api/v1/device-groups` | 创建设备分组 | ✓ |
| PUT | `/api/v1/device-groups/{id}` | 更新设备分组 | ✓ |
| DELETE | `/api/v1/device-groups/{id}` | 删除设备分组 | ✓ |
| GET | `/api/v1/tags` | 标签列表 | ✓ |
| POST | `/api/v1/tags` | 创建标签 | ✓ |
| PUT | `/api/v1/tags/{id}` | 更新标签 | ✓ |
| DELETE | `/api/v1/tags/{id}` | 删除标签 | ✓ |
| GET | `/api/v1/tags/media/{id}` | 获取素材标签 | ✓ |
| PUT | `/api/v1/tags/media/{id}` | 设置素材标签 | ✓ |
| GET | `/api/v1/auth/users` | 用户列表（管理员） | ✓ |
| POST | `/api/v1/auth/users` | 创建用户（管理员） | ✓ |
| PUT | `/api/v1/auth/users/{id}` | 更新用户（管理员） | ✓ |
| DELETE | `/api/v1/auth/users/{id}` | 删除用户（管理员） | ✓ |
| GET | `/api/v1/audit/list` | 操作日志查询 | ✓ |
| GET | `/api/v1/power-schedules` | 开关机计划列表 | ✓ |
| POST | `/api/v1/power-schedules` | 创建开关机计划 | ✓ |
| PUT | `/api/v1/power-schedules/{id}` | 更新开关机计划 | ✓ |
| PATCH | `/api/v1/power-schedules/{id}` | 启用/禁用开关机计划 | ✓ |
| DELETE | `/api/v1/power-schedules/{id}` | 删除开关机计划 | ✓ |
| GET | `/api/v1/command-logs` | 下发记录查询 | ✓ |
| GET | `/api/v1/player/sync/{id}` | Player 同步排程 | ✕ |
| GET | `/api/v1/player/download/{path}` | 素材下载 | ✕ |
| GET | `/api/v1/player/events/{id}` | SSE 实时推送（长连接） | ✕ |
| GET | `/health` | 健康检查 | ✕ |

在线 API 文档：启动 Server 后访问 `http://<IP>:8000/api/docs`

---

## ⚙️ 配置说明

配置文件：`shared/config.py`

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `sync_interval_seconds` | 30 | Player 排程轮询间隔 |
| `heartbeat_interval_seconds` | 30 | Player 心跳上报间隔 |
| `heartbeat_timeout_minutes` | 2 | 屏幕离线判定超时 |
| `screenshot_interval_seconds` | 60 | 自动截图间隔 |
| `screenshot_quality` | 75 | 截图 JPEG 质量 (0-100) |
| `transition_duration_ms` | 800 | 过渡动画时长 |
| `player_cache_dir` | `player_cache/` | Player 本地缓存目录 |
| `upload_dir` | `uploads/` | Server 素材存储目录 |
| `token_expire_days` | 7 | 登录 Token 有效期（天） |

---

## ❓ 常见问题

<details>
<summary><b>播放器启动后黑屏？</b></summary>
检查 Server 是否可达：浏览器访问 http://IP:8000/api/v1/displays/list。如果 Server 正常，检查防火墙是否放行 8000 端口。
</details>

<details>
<summary><b>服务器离线后播放器还能用吗？</b></summary>
可以。Player 会自动缓存每次同步的排程和素材到本地。服务器离线后，Player 继续播放上次缓存的内容，角落显示「⚠ 离线模式」提示。服务器恢复后自动同步更新，离线提示自动消失。
</details>

<details>
<summary><b>图片有黑边怎么办？</b></summary>
在布局编辑器中，每个区域可以选择填充模式：「裁切」（无黑边，裁掉超出部分）、「适应」（保持比例，可能有黑边）、「拉伸」（填满，可能变形）。默认为「裁切」。
</details>

<details>
<summary><b>横屏和竖屏能混用吗？</b></summary>
可以。创建布局时选择对应的分辨率（1920×1080 横屏 或 1080×1920 竖屏），Player 会自动适配。屏幕分辨率由 Player 自动上报。
</details>

<details>
<summary><b>PPT 转换效果不好？</b></summary>
PPT 转换有两种模式：优先使用 LibreOffice（质量最好），fallback 到 python-pptx。建议安装 <a href="https://www.libreoffice.org/download/">LibreOffice</a> 以获得最佳效果。安装后会自动检测。
</details>

<details>
<summary><b>PPT 只播放第一页怎么办？</b></summary>
PPT 上传后会自动转换为图片序列，默认轮播所有页。如果只播放第一页，请检查布局编辑器中的 PPT 播放设置：<br>
1. 选择 PPT 素材后，展开"PPT 播放设置"面板<br>
2. 确认播放模式为"轮播全部页"（默认）<br>
3. 如果选择了"固定某一页"，则只会显示指定的那一页<br>
4. 每页播放时长可在"播放时长(秒)"中修改
</details>

<details>
<summary><b>视频无法播放？</b></summary>
Qt Multimedia 依赖系统解码器。MP4 (H.264) 在 Windows 10+ 上原生支持。WebM/MKV 可能需要安装 <a href="https://codecguide.com/download_kl.htm">K-Lite Codec Pack</a>。
</details>

<details>
<summary><b>如何修改 Player 的服务器地址？</b></summary>
两种方式：<br>1. 双击 exe 时加 <code>--config</code> 参数，弹出配置窗口重新输入<br>2. 直接编辑 exe 同级目录下的 <code>player_config.json</code>
</details>

<details>
<summary><b>屏幕离线了管理后台还显示在线？</b></summary>
Server 每 60 秒检查一次心跳，超过 2 分钟没心跳的屏幕会自动标记为离线。可在 <code>shared/config.py</code> 中修改 <code>heartbeat_timeout_minutes</code>。
</details>

<details>
<summary><b>忘记管理后台密码？</b></summary>
在服务器控制台执行：<code>signboard-server.exe --reset-password admin</code><br>密码会重置为随机值并打印到控制台。
</details>

<details>
<summary><b>登录后多久需要重新登录？</b></summary>
Token 有效期 7 天，过期后自动跳转登录页。修改密码会立即踢掉所有其他设备的登录，需要重新输入密码。
</details>

<details>
<summary><b>如何更新管理后台前端？</b></summary>
打包部署后，将新的前端文件放入 exe 同级的 <code>server/templates/admin/</code> 目录（包括 <code>index.html</code> 和 <code>assets/</code>），刷新浏览器即可生效，无需重新打包 EXE。如果外置目录不存在，自动使用 exe 内嵌版本。
</details>

<details>
<summary><b>打包后 EXE 显示空白页 / 无法登录？</b></summary>
启动 Server 后访问 <code>/health</code> 接口检查模板路径是否正确。控制台会打印诊断信息（模板目录、index.html 是否存在）。确认 <code>server/templates/admin/index.html</code> 文件存在。
</details>

<details>
<summary><b>紧急插播没有立即生效？</b></summary>
紧急插播通过 SSE 实时推送到 Player，正常情况下 1-2 秒内生效。如果延迟较长，检查 Server 和 Player 之间的网络是否通畅，以及防火墙是否放行 8000 端口。Player 也有 30 秒轮询兜底。
</details>

<details>
<summary><b>日历视图看不到今天的排程？</b></summary>
确认排程的「开始时间」早于今天且「结束时间」晚于今天（或留空）。如果排程是今天刚创建的，检查时间是否设置正确。
</details>

<details>
<summary><b>支持多少台屏幕？</b></summary>
理论上无上限，SQLite 和 30 秒轮询对于 50+ 台屏幕没有压力。实际测试过 20 台。
</details>

<details>
<summary><b>Android 播放器如何安装？</b></summary>
1. 将 <code>app-debug.apk</code> 传输到 Android 设备<br>
2. 在设备上安装 APK（需允许"未知来源"）<br>
3. 打开 App，输入服务器地址和屏幕名称<br>
4. 点击"启动"即可<br>
5. 支持开机自启（需在设置中开启）
</details>

<details>
<summary><b>Android 播放器支持哪些功能？</b></summary>
支持全屏播放图片/视频、4 种布局模板、PPT 多图轮播、走马灯、SSE 实时推送、离线播放、熄屏/唤醒控制、重启（需 Root）、看门狗（自动重启）。
</details>

---

## 📝 版本历史

### v2.2.1（2026-06-15 ~ 2026-06-16）

**开关机计划（新增）：**
- 独立开关机计划管理页面（卡片/列表视图切换）
- 按设备或全部设备绑定，支持自定义执行日（周日~周六）
- 开机/关机时间可独立配置，支持"不控制"选项
- 启用/禁用开关
- Server 后台每 60 秒自动调度，匹配时间下发 screen_on/screen_off 命令

**下发记录（新增）：**
- 全局下发记录页面，记录所有命令下发（屏幕管理手动操作 + 开关机计划自动调度）
- 支持按设备、命令类型、触发方式筛选
- 分页查询
- 设置页新增"下发记录"Tab

**Windows 播放器修复：**
- 熄屏/唤醒：改用 Win32 API `SendMessageW(SC_MONITORPOWER)` 实现立即熄屏/唤醒
- 修复 `RemoteControl` 每次新建实例导致状态丢失（`_is_screen_off` 永远为 False）
- 唤醒后屏幕超时恢复为"从不"（`powercfg 0`）
- SSE 命令事件实时解析执行（不再等 30 秒轮询）

**Android 播放器新增：**
- 双击返回键退出（2 秒内双击，防止误操作）
- 角落点击 5 次跳转设置页面（四角 100dp 区域）
- 唤醒后恢复原始屏幕超时（`SCREEN_OFF_TIMEOUT`）

**Bug 修复：**
- 素材改名/屏幕改名提示"请求失败"但实际成功（`request` 参数缺失导致 `log_action` 报错）

### v2.2（2026-06-13 ~ 2026-06-14）

**设备管理增强：**
- 设备分组管理（按区域/用途分组，标签筛选）
- 批量操作（绑定/取消布局、绑定/取消排程、重启、熄屏、唤醒、删除）
- 设备列表视图（表格排版，支持搜索和状态筛选）
- 设备绑定信息显示（布局名+排程名，可点击跳转）
- 布局/排程点击快速跳转到编辑页面

**素材管理增强：**
- 素材标签分组（标签筛选栏+标签管理弹窗）
- 批量打标签/取消标签
- 素材列表视图（标签列、分辨率列）
- 图片/视频分辨率自动获取（上传时检测）
- 视频缩略图显示（视频首帧+播放图标）
- 素材预览弹窗（支持PPT多页翻页）
- 素材过期时间（自动清理过期素材）

**布局设计重构：**
- 三栏编辑器（属性+预览+素材库）
- 分辨率快捷按钮（横屏1920x1080/竖屏1080x1920）
- 素材库搜索+类型筛选
- 绑定素材缩略图预览（点击可查看详情）
- PPT播放模式设置（轮播/固定页码+每页时长）
- 网页组件（嵌入网页URL）
- 预览区使用原图（不再是缩略图）
- 打开编辑器默认选中区域1

**用户权限与审计（P0）：**
- 多用户角色：管理员（全部权限）、操作员（素材/布局/排程）、只读
- 用户管理页面（创建/编辑/删除用户）
- 操作日志（登录/创建/更新/删除自动记录用户名和IP）
- 日志查看器（按资源/操作/用户筛选）
- 素材标签管理（创建/编辑/删除/颜色）

**素材过期：**
- 后台定时任务自动清理过期素材
- 更新API支持设置/清除过期时间

**设置页面重构：**
- 三个Tab（修改密码/操作日志/标签管理）
- 右上角按钮改为"更多"

**播放器改进：**
- Windows 播放器分辨率DPI修正（物理分辨率）
- Windows 播放器MAC地址上报
- Windows 播放器支持网页组件
- Android 心跳补全 display_id/platform/ip
- Android MAC地址上报
- 设备名称双向同步（前端改名→播放器自动更新）

**其他优化：**
- 视频上传自动获取分辨率（OpenCV）
- 布局/排程点击跳转编辑页面
- 列表视图模式记忆（localStorage）
- 操作日志全CRUD覆盖（创建/更新/删除/登录）

### v2.1.1（2026-06-13）

**Android 端重大更新：**
- 熄屏/唤醒功能（Root + input keyevent，立即生效）
- 服务器重启后自动重新注册（检测 401）
- 离线播放支持（保存同步数据，断网后继续播放）
- SSE 命令实时推送（截屏/熄屏/唤醒/重启）
- 图片加载优化（异步加载 + 采样率 + 重试机制）
- 服务器地址修复（不再硬编码 10.0.2.2）
- 权限请求优化（启动时引导开启）
- MediaProjection 截图功能

**Server 修复：**
- 新增 heartbeat 端点
- 新增 schedule count API
- 修复 player_paths 路径匹配
- 心跳超时从 2 分钟改为 1 分钟

**前端更新：**
- 截屏按钮改为 command 接口
- 修改设备名称功能
- 新增 schedule count 方法
- axios withCredentials 配置
- 设备信息显示（平台/IP/MAC）

**设备管理：**
- 设备平台显示（Windows/Android 标签）
- 设备 IP 地址显示
- 设备信息详情弹窗
- 心跳超时从 2 分钟改为 1 分钟

### v2.1.1（2026-06-12）

**Android 端全面修复：**
- 修复素材黑屏（getBaseUrl 硬编码模拟器地址）
- 修复 ANR（下载完成后再显示布局）
- 修复 Android 7.0 闪退（移除前台服务要求）
- 新增开机自启动（BootReceiver）
- 新增看门狗功能（PlayerService 定时检测）
- 首次配置后自动连接（不再每次点击启动）

**屏幕管理功能：**
- Server 新增命令 API（POST /command）
- Server 新增修改设备名称 API（PUT /{id}）
- Android 端支持接收并执行命令（截屏/熄屏/唤醒/重启）
- 前端新增修改设备名称按钮

### v2.1（2026-06-11）

**Android 播放器：**
- 新增 Android 播放器客户端（Kotlin + ExoPlayer）
- 支持全屏播放图片/视频，4 种布局模板
- PPT 多图轮播（轮播/固定模式）
- 前台 Service 看门狗（Activity 退出自动重启）
- 远程控制（熄屏/唤醒/重启，Root 权限）
- 开机自启

**远程控制：**
- 新增熄屏/唤醒/重启指令（二次确认）
- Windows Player 新增 remote_control.py 模块
- 前端屏幕管理新增熄屏/唤醒按钮

**PPT 多图轮播：**
- PPT 上传后自动转换为图片序列，支持全部页轮播
- 新增固定模式：可指定某一页一直播放
- 每页播放时长可配置（素材级 + 布局级覆盖）
- 布局编辑器新增 PPT 配置面板

**代码审查修复（15 项）：**
- P0：淡入动画时长 Bug、密码时序攻击、上传文件大小限制
- P1：audio.py signal 泄漏、初始密码明文存储、Cookie secure 标志、async 阻塞事件循环、跨线程锁
- P2：SSE 超时、错误提示统一（alert → Toast）、轮询指数退避
- P3：构建脚本去重（新建 build_common.py）

**新增：**
- Toast 通知组件（右上角浮层，替代 alert 弹窗）
- 构建共享模块（build_common.py）

### v2.0（2026-06-08）

**架构升级：**
- 前端从单文件 HTML 迁移到 Vue 3 + Vite + Pinia + Vue Router
- 新增日历视图、排程重复、紧急插播、SSE 实时推送
- PPT 上传自动转图、截图历史保留、过期 Token 自动清理

**修复（48 项代码审查）：**
- P0：路径遍历漏洞、截图上传鉴权、Dashboard 数据错误、排程 PATCH 接口
- P1：CORS 收紧、密码随机生成、跨天排程、MAC 地址去重、引用检查
- P2：Pydantic 验证、修改密码页面、SQLite WAL、大文件分块上传

**运行时修复（6 项）：**
- 客户端连接失败（datetime 导入丢失）
- PPT 黑屏（file_path 指向目录）
- 紧急插播时间偏差（UTC vs 本地时间）
- PPT 无法删除（os.remove 不能删目录）
- 布局/插播不刷新（轮询未启动 + layout_key 不含 schedule_id + SSE 跨线程不安全）
- 日历当天排程不显示（datetime vs date 比较）

### v1.1.2（2026-06-05）

- 离线播放深度修复（6 个场景全覆盖）
- 管理后台 UI 全屏修复
- 打包脚本适配

### v1.1.1（2026-06-05）

- Token 过期 + 改密码踢人
- 离线播放运行时 fallback
- 模板外置分离

### v1.1（2026-06-04）

- 管理后台登录鉴权
- 离线播放
- 素材预览

### v1.0（2026-06-03）

- 初始版本：Server + Player + Web 管理后台

---

## 📄 许可证

MIT License

---

**Built with ❤️ using Python, PyQt6, Vue 3, and FastAPI.**
