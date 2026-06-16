# SignBoard Android Player

SignBoard 数字标牌系统的 Android 播放器客户端。

## 功能

- 全屏播放图片/视频
- 支持 4 种布局（全屏轮播、播放列表、左右分屏、上下分屏）
- PPT 多图轮播（轮播/固定模式）
- 走马灯文字滚动
- SSE 实时推送 + 30 秒轮询兜底
- 离线播放（服务器离线时播放缓存内容）
- 远程控制（熄屏/唤醒/重启）
- 看门狗（前台 Service，Activity 退出自动重启）
- 开机自启

## 环境要求

- Android Studio Hedgehog (2023.1.1) 或更高版本
- JDK 17
- Android SDK 34
- 设备 Android 7.0+ (API 24)

## 构建

1. 用 Android Studio 打开 `android-player` 目录
2. 等待 Gradle 同步完成
3. Build → Build Bundle(s) / APK(s) → Build APK(s)

## 配置

### 服务器地址

在 `app/build.gradle.kts` 中修改：

```kotlin
buildConfigField("String", "BASE_URL", "\"http://your-server:8000\"")
```

或在 App 中运行时修改。

### 签名

在 `app/build.gradle.kts` 中配置签名：

```kotlin
signingConfigs {
    create("release") {
        storeFile = file("keystore.jks")
        storePassword = System.getenv("KEYSTORE_PASSWORD") ?: ""
        keyAlias = System.getenv("KEY_ALIAS") ?: ""
        keyPassword = System.getenv("KEY_PASSWORD") ?: ""
    }
}
```

## 项目结构

```
android-player/
├── app/src/main/
│   ├── java/com/signboard/player/
│   │   ├── SignBoardApp.kt          # Application
│   │   ├── MainActivity.kt          # 配置界面
│   │   ├── PlayerActivity.kt        # 播放界面
│   │   ├── BootReceiver.kt          # 开机自启
│   │   ├── service/
│   │   │   └── PlayerService.kt     # 前台 Service + 看门狗
│   │   ├── sync/
│   │   │   ├── SyncManager.kt       # 排程同步
│   │   │   ├── SseClient.kt         # SSE 长连接
│   │   │   └── MediaDownloader.kt   # 素材下载
│   │   ├── player/
│   │   │   ├── PlayerView.kt        # 播放器接口
│   │   │   ├── ImagePlayer.kt       # 图片播放
│   │   │   ├── VideoPlayer.kt       # 视频播放
│   │   │   ├── MarqueeView.kt       # 走马灯
│   │   │   └── LayoutManager.kt     # 布局管理
│   │   ├── control/
│   │   │   └── RemoteControl.kt     # 远程控制
│   │   ├── model/
│   │   │   └── Models.kt            # 数据模型
│   │   └── api/
│   │       ├── ApiService.kt        # API 接口
│   │       └── ApiClient.kt         # API 客户端
│   ├── res/
│   │   ├── layout/
│   │   │   ├── activity_main.xml
│   │   │   └── activity_player.xml
│   │   └── values/
│   │       ├── strings.xml
│   │       ├── colors.xml
│   │       └── themes.xml
│   └── AndroidManifest.xml
├── build.gradle.kts
└── settings.gradle.kts
```

## 使用

1. 启动 App
2. 输入服务器地址和屏幕名称
3. 点击「启动」
4. 自动注册并开始播放

## 注意事项

- 重启功能需要 Root 权限
- 熄屏/唤醒需要 `WRITE_SETTINGS` 权限
- 首次运行需要授予存储权限
