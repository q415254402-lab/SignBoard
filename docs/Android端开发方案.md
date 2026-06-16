# SignBoard Android 端开发方案

> 版本：v1.0 | 日期：2026-06-11 | 作者：MiMo Code

---

## 一、项目概述

### 1.1 目标

为 SignBoard 数字标牌系统开发 Android 播放器客户端，支持在 Android 设备上全屏播放内容，与现有 Windows Player 功能对齐。

### 1.2 设计原则

- **复用现有 API**：不改动后端核心逻辑，仅新增枚举值
- **独立项目**：Android 项目与现有代码完全隔离
- **功能对齐**：支持现有所有播放功能（图片/视频/走马灯/布局/离线）
- **扩展功能**：新增看门狗（前台 Service）、熄屏/唤醒控制

### 1.3 影响范围

| 模块 | 影响 | 说明 |
|------|------|------|
| Server 后端 | 极小 | 仅新增 2 个枚举值（`screen_off`、`screen_on`） |
| 前端管理后台 | 极小 | 仅新增 2 个按钮 + 二次确认弹窗 |
| Windows Player | 极小 | 仅新增 1 个模块（`remote_control.py`） |
| Android 项目 | 无 | 独立项目，完全隔离 |

---

## 二、技术选型

| 模块 | 技术 | 版本要求 | 说明 |
|------|------|----------|------|
| 语言 | Kotlin | 1.8+ | 官方推荐，协程支持好 |
| 最低版本 | Android 7.0 | API 24 | 覆盖 95%+ 设备 |
| 目标版本 | Android 13 | API 33 | 最新稳定版 |
| 图片加载 | Coil | 2.x | Kotlin 原生，协程支持 |
| 视频播放 | ExoPlayer | 1.x | Google 官方，支持多种格式 |
| 网络请求 | OkHttp + Retrofit | 4.x / 2.x | 成熟稳定 |
| SSE | OkHttp (streaming) | 4.x | 长连接支持 |
| JSON | Gson | 2.x | 数据解析 |
| 数据库 | Room | 2.x | 本地缓存排程/素材信息 |
| 依赖注入 | Hilt | 2.x | 可选，简化依赖管理 |

### 2.1 依赖清单

```gradle
// app/build.gradle.kts
dependencies {
    // AndroidX
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-service:2.7.0")
    
    // 网络
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    
    // JSON
    implementation("com.google.code.gson:gson:2.10.1")
    
    // 图片
    implementation("io.coil-kt:coil:2.5.0")
    
    // 视频播放
    implementation("androidx.media3:media3-exoplayer:1.2.1")
    implementation("androidx.media3:media3-ui:1.2.1")
    
    // 数据库
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    annotationProcessor("androidx.room:room-compiler:2.6.1")
    
    // 协程
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
```

---

## 三、功能模块

### 3.1 功能清单

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 屏幕注册 | P0 | 首次启动注册，获取 display_id + player_token |
| 排程同步 | P0 | HTTP 轮询（30秒）+ SSE 实时推送 |
| 素材下载 | P0 | 下载图片/视频到本地缓存 |
| 图片播放 | P0 | 支持轮播、淡入淡出、填充模式 |
| 视频播放 | P0 | ExoPlayer 全屏播放，支持音量控制 |
| 走马灯 | P1 | 文字滚动，可配颜色/速度/字体 |
| 布局系统 | P0 | 全屏轮播、播放列表、左右分屏、上下分屏 |
| 离线缓存 | P1 | Room 数据库缓存排程/素材信息 |
| 离线播放 | P1 | 服务器离线时播放缓存内容 |
| 心跳上报 | P0 | 30秒间隔，上报状态 |
| 截图上报 | P1 | 60秒自动截图 + 手动触发 |
| 熄屏控制 | P1 | 远程熄屏/唤醒 |
| 重启控制 | P1 | Root 权限重启 |
| 看门狗 | P1 | 前台 Service，Activity 退出自动重启 |
| 开机自启 | P2 | Service 自启动 |

### 3.2 功能对比（Windows vs Android）

| 功能 | Windows Player | Android Player |
|------|----------------|----------------|
| 图片渲染 | QGraphicsOpacityEffect | ImageView + Animation |
| 视频播放 | QMediaPlayer | ExoPlayer (Media3) |
| 走马灯 | QPainter 自绘 | TextView + Animation |
| 全屏 | FramelessWindow | WindowInsetsController |
| 后台运行 | 不支持 | 前台 Service |
| 截图 | QPixmap.grabWindow | MediaProjection API |
| 看门狗 | 不支持 | 前台 Service |
| 熄屏/唤醒 | Windows API | PowerManager |
| 重启 | shutdown 命令 | Root (su reboot) |

---

## 四、项目结构

```
SignBoardPlayer/
├── app/
│   ├── src/main/
│   │   ├── java/com/signboard/player/
│   │   │   ├── SignBoardApp.kt              # Application
│   │   │   ├── MainActivity.kt              # 入口，配置界面
│   │   │   ├── PlayerActivity.kt            # 全屏播放界面
│   │   │   ├── service/
│   │   │   │   └── PlayerService.kt         # 前台 Service + 看门狗
│   │   │   ├── sync/
│   │   │   │   ├── SyncManager.kt           # 排程同步
│   │   │   │   ├── SseClient.kt             # SSE 长连接
│   │   │   │   └── MediaDownloader.kt       # 素材下载
│   │   │   ├── player/
│   │   │   │   ├── LayoutManager.kt         # 布局管理
│   │   │   │   ├── ImagePlayer.kt           # 图片播放
│   │   │   │   ├── VideoPlayer.kt           # 视频播放
│   │   │   │   ├── MarqueeView.kt           # 走马灯
│   │   │   │   └── SplitLayout.kt           # 分屏布局
│   │   │   ├── control/
│   │   │   │   └── RemoteControl.kt         # 熄屏/唤醒/重启
│   │   │   ├── model/
│   │   │   │   ├── SyncResponse.kt          # 同步响应模型
│   │   │   │   ├── Schedule.kt              # 排程模型
│   │   │   │   ├── Layout.kt                # 布局模型
│   │   │   │   ├── Zone.kt                  # 区域模型
│   │   │   │   └── Media.kt                 # 素材模型
│   │   │   ├── db/
│   │   │   │   ├── AppDatabase.kt           # Room 数据库
│   │   │   │   ├── ScheduleDao.kt           # 排程 DAO
│   │   │   │   └── MediaDao.kt              # 素材 DAO
│   │   │   ├── api/
│   │   │   │   ├── ApiService.kt            # Retrofit API 接口
│   │   │   │   └── ApiClient.kt             # API 客户端
│   │   │   └── util/
│   │   │       ├── NetworkUtil.kt           # 网络工具
│   │   │       ├── ScreenUtil.kt            # 屏幕信息
│   │   │       └── Logger.kt                # 日志工具
│   │   ├── res/
│   │   │   ├── layout/
│   │   │   │   ├── activity_main.xml        # 配置界面
│   │   │   │   ├── activity_player.xml      # 播放界面
│   │   │   │   └── view_marquee.xml         # 走马灯视图
│   │   │   ├── values/
│   │   │   │   ├── strings.xml
│   │   │   │   ├── colors.xml
│   │   │   │   └── themes.xml
│   │   │   └── drawable/
│   │   │       └── ic_player.xml
│   │   └── AndroidManifest.xml
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── gradle/
│   └── libs.versions.toml
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

---

## 五、核心模块设计

### 5.1 同步模块

#### 5.1.1 SyncManager

```kotlin
class SyncManager(
    private val apiService: ApiService,
    private val mediaDao: MediaDao,
    private val context: Context
) {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var syncJob: Job? = null
    private var sseJob: Job? = null
    
    // 事件回调
    val scheduleUpdated = MutableSharedFlow<SyncResponse>()
    val connectionChanged = MutableSharedFlow<ConnectionState>()
    
    fun start(displayId: Int, token: String) {
        // 首次同步
        scope.launch {
            doSync(displayId, token)
        }
        
        // 启动轮询
        syncJob = scope.launch {
            while (isActive) {
                delay(30_000)  // 30秒
                doSync(displayId, token)
            }
        }
        
        // 启动 SSE
        startSse(displayId, token)
    }
    
    private suspend fun doSync(displayId: Int, token: String) {
        try {
            connectionChanged.emit(ConnectionState.CONNECTING)
            
            val response = apiService.sync(displayId, "Bearer $token")
            if (response.isSuccessful) {
                val data = response.body()!!
                
                // 缓存到本地
                cacheToLocal(data)
                
                // 下载素材
                downloadMedia(data.mediaList, token)
                
                connectionChanged.emit(ConnectionState.CONNECTED)
                scheduleUpdated.emit(data)
            } else {
                connectionChanged.emit(ConnectionState.ERROR)
                tryOfflineFallback()
            }
        } catch (e: Exception) {
            connectionChanged.emit(ConnectionState.ERROR)
            tryOfflineFallback()
        }
    }
    
    private fun startSse(displayId: Int, token: String) {
        sseJob = scope.launch {
            SseClient.connect(
                url = "${BuildConfig.BASE_URL}/api/v1/player/events/$displayId",
                token = token,
                onEvent = { 
                    scope.launch { doSync(displayId, token) }
                },
                onDisconnected = {
                    // SSE 断开，继续轮询
                }
            )
        }
    }
    
    private suspend fun downloadMedia(mediaList: List<Media>, token: String) {
        for (media in mediaList) {
            val localPath = File(context.cacheDir, "media/${media.filePath}")
            if (!localPath.exists()) {
                MediaDownloader.download(
                    url = "${BuildConfig.BASE_URL}/api/v1/player/download/${media.filePath}",
                    token = token,
                    outputFile = localPath
                )
            }
            // 下载 PPT 所有图片
            media.pptImages?.forEach { imgPath ->
                val localImgPath = File(context.cacheDir, "media/$imgPath")
                if (!localImgPath.exists()) {
                    MediaDownloader.download(
                        url = "${BuildConfig.BASE_URL}/api/v1/player/download/$imgPath",
                        token = token,
                        outputFile = localImgPath
                    )
                }
            }
        }
    }
    
    private suspend fun tryOfflineFallback() {
        // 从本地缓存加载上次同步数据
        val cached = mediaDao.getLastSync()
        if (cached != null) {
            scheduleUpdated.emit(cached)
        }
    }
    
    fun stop() {
        syncJob?.cancel()
        sseJob?.cancel()
        scope.cancel()
    }
}
```

#### 5.1.2 SSE 客户端

```kotlin
class SseClient {
    
    companion object {
        suspend fun connect(
            url: String,
            token: String,
            onEvent: () -> Unit,
            onDisconnected: () -> Unit
        ) {
            val client = OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS)  // 无限超时
                .build()
            
            val request = Request.Builder()
                .url(url)
                .addHeader("Authorization", "Bearer $token")
                .build()
            
            var backoff = 1000L
            
            while (true) {
                try {
                    client.newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            backoff = 1000L
                            
                            response.body?.byteStream()?.bufferedReader()?.forEachLine { line ->
                                if (line.startsWith("data:")) {
                                    onEvent()
                                }
                            }
                        }
                    }
                } catch (e: Exception) {
                    // 连接失败，指数退避
                    delay(backoff)
                    backoff = minOf(backoff * 2, 60_000L)
                }
                
                onDisconnected()
            }
        }
    }
}
```

### 5.2 播放模块

#### 5.2.1 LayoutManager

```kotlin
class LayoutManager(private val context: Context) {
    
    private var currentLayout: Layout? = null
    private var currentWidget: View? = null
    
    fun switchLayout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>,
        container: ViewGroup
    ) {
        // 清除旧布局
        currentWidget?.let {
            (it as? PlayerView)?.stop()
            container.removeView(it)
        }
        
        // 根据类型创建新布局
        currentLayout = layout
        currentWidget = when (layout.type) {
            "fullscreen" -> createFullscreenLayout(layout, mediaPaths, mediaList)
            "playlist" -> createPlaylistLayout(layout, mediaPaths, mediaList)
            "split_2" -> createSplit2Layout(layout, mediaPaths, mediaList)
            "split_3" -> createSplit3Layout(layout, mediaPaths, mediaList)
            else -> null
        }
        
        currentWidget?.let {
            container.addView(it, ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            ))
            (it as? PlayerView)?.start()
        }
    }
    
    private fun createFullscreenLayout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        return FullscreenPlayer(context).apply {
            configure(layout.zones, mediaPaths, mediaList)
        }
    }
    
    private fun createPlaylistLayout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        return PlaylistPlayer(context).apply {
            configure(layout.zones, mediaPaths, mediaList)
        }
    }
    
    private fun createSplit2Layout(
        layout: Layout,
        mediaPaths: Map Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        return Split2Player(context).apply {
            configure(layout.zones, mediaPaths, mediaList)
        }
    }
    
    private fun createSplit3Layout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        return Split3Player(context).apply {
            configure(layout.zones, mediaPaths, mediaList, layout.marquee)
        }
    }
    
    fun stop() {
        (currentWidget as? PlayerView)?.stop()
    }
}
```

#### 5.2.2 ImagePlayer

```kotlin
class ImagePlayer(private val context: Context) : FrameLayout(context), PlayerView {
    
    private val imageView = ImageView(context)
    private var zones: List<Zone> = emptyList()
    private var mediaPaths: Map<Int, File> = emptyMap()
    private var currentIndex = 0
    private var timer: Job? = null
    
    // PPT 相关
    private var pptMode: String? = null
    private var pptSlideIndex: Int = 0
    
    init {
        addView(imageView, LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT
        ))
        imageView.scaleType = ImageView.ScaleType.FIT_CENTER
    }
    
    fun configure(
        zones: List<Zone>,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ) {
        this.zones = zones
        this.mediaPaths = mediaPaths
        this.currentIndex = 0
    }
    
    override fun start() {
        showCurrent()
    }
    
    override fun stop() {
        timer?.cancel()
    }
    
    private fun showCurrent() {
        if (zones.isEmpty()) return
        
        val zone = zones[currentIndex]
        val mediaId = zone.mediaId ?: return
        val file = mediaPaths[mediaId] ?: return
        
        // 检查 PPT 模式
        pptMode = zone.pptMode
        if (pptMode == "fixed") {
            // 固定模式：显示指定页
            pptSlideIndex = zone.pptSlideIndex ?: 0
            // 加载指定页图片
        } else {
            // 轮播模式：根据当前页码显示
            val currentSlide = zone._pptSlideIndex ?: 0
            // 加载对应页图片
        }
        
        // 加载图片
        val uri = Uri.fromFile(file)
        imageView.setImageURI(uri)
        
        // 应用填充模式
        imageView.scaleType = when (zone.fillMode) {
            "fill" -> ImageView.ScaleType.CENTER_CROP
            "stretch" -> ImageView.ScaleType.FIT_XY
            else -> ImageView.ScaleType.FIT_CENTER
        }
        
        // 启动定时器
        val duration = zone.durationSeconds * 1000L
        timer = CoroutineScope(Dispatchers.Main).launch {
            delay(duration)
            next()
        }
    }
    
    private fun next() {
        val zone = zones[currentIndex]
        
        // 检查是否是 PPT 轮播
        if (pptMode != "fixed" && zone.pptImages != null) {
            val currentSlide = zone._pptSlideIndex ?: 0
            if (currentSlide < zone.pptImages.size - 1) {
                // 还有下一页
                zone._pptSlideIndex = currentSlide + 1
            } else {
                // 已到最后一页，切换到下一个 zone
                zone._pptSlideIndex = 0
                currentIndex = (currentIndex + 1) % zones.size
            }
        } else {
            // 普通素材：切换到下一个 zone
            currentIndex = (currentIndex + 1) % zones.size
        }
        
        showCurrent()
    }
}
```

#### 5.2.3 VideoPlayer

```kotlin
class VideoPlayer(private val context: Context) : FrameLayout(context), PlayerView {
    
    private val exoPlayer = ExoPlayer.Builder(context).build()
    private val playerView = PlayerView(context)
    
    init {
        playerView.player = exoPlayer
        addView(playerView, LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT
        ))
        
        // 循环播放
        exoPlayer.repeatMode = Player.REPEAT_MODE_ALL
    }
    
    fun configure(zone: Zone, file: File) {
        val mediaItem = MediaItem.fromUri(Uri.fromFile(file))
        exoPlayer.setMediaItem(mediaItem)
        exoPlayer.volume = zone.volume / 100f
    }
    
    override fun start() {
        exoPlayer.prepare()
        exoPlayer.play()
    }
    
    override fun stop() {
        exoPlayer.stop()
        exoPlayer.release()
    }
}
```

#### 5.2.4 MarqueeView

```kotlin
class MarqueeView(context: Context) : View(context) {
    
    private var text = ""
    private var speed = 60f  // px/s
    private var fontSize = 28f
    private var fontColor = Color.WHITE
    private var bgColor = Color.BLACK
    
    private var offset = 0f
    private var textWidth = 0f
    
    private val paint = Paint().apply {
        isAntiAlias = true
    }
    
    private val timer = object : Runnable {
        override fun run() {
            offset -= speed / 30f  // 30fps
            if (offset < -textWidth) {
                offset = width.toFloat()
            }
            invalidate()
            postDelayed(this, 33)  // ~30fps
        }
    }
    
    fun configure(
        text: String,
        speed: Int = 60,
        fontSize: Int = 28,
        fontColor: String = "#FFFFFF",
        bgColor: String = "#000000"
    ) {
        this.text = text
        this.speed = speed.toFloat()
        this.fontSize = fontSize.toFloat()
        this.fontColor = Color.parseColor(fontColor)
        this.bgColor = Color.parseColor(bgColor)
        
        paint.textSize = this.fontSize
        textWidth = paint.measureText(text)
        
        post { offset = width.toFloat() }
    }
    
    fun start() {
        post(timer)
    }
    
    fun stop() {
        removeCallbacks(timer)
    }
    
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        
        // 绘制背景
        canvas.drawColor(bgColor)
        
        // 绘制文字
        paint.color = fontColor
        val y = (height + fontSize) / 2 - 4
        canvas.drawText(text, offset, y, paint)
    }
}
```

### 5.3 控制模块

#### 5.3.1 RemoteControl

```kotlin
class RemoteControl(private val context: Context) {
    
    private var isScreenOff = false
    
    /**
     * 熄屏
     */
    fun screenOff(): Boolean {
        if (isScreenOff) return true  // 幂等
        
        return try {
            // 方案 A：设置屏幕超时为 1 秒
            Settings.System.putInt(
                context.contentResolver,
                Settings.System.SCREEN_OFF_TIMEOUT, 1000
            )
            isScreenOff = true
            true
        } catch (e: Exception) {
            Log.e(TAG, "熄屏失败", e)
            false
        }
    }
    
    /**
     * 唤醒
     */
    fun screenOn(): Boolean {
        if (!isScreenOff) return true  // 幂等
        
        return try {
            // 恢复屏幕超时
            Settings.System.putInt(
                context.contentResolver,
                Settings.System.SCREEN_OFF_TIMEOUT,
                60 * 60 * 1000  // 1小时
            )
            
            // 点亮屏幕
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            val wakeLock = powerManager.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP,
                "signboard:screen_on"
            )
            wakeLock.acquire(10 * 1000L)
            
            isScreenOff = false
            true
        } catch (e: Exception) {
            Log.e(TAG, "唤醒失败", e)
            false
        }
    }
    
    /**
     * 重启设备
     */
    fun restart(): Boolean {
        return try {
            // 方案 C: Root 权限
            val process = Runtime.getRuntime().exec("su -c reboot")
            val exitCode = process.waitFor()
            exitCode == 0
        } catch (e: Exception) {
            Log.e(TAG, "重启失败", e)
            false
        }
    }
    
    /**
     * 检查 Root 权限
     */
    fun isRootAvailable(): Boolean {
        return try {
            val process = Runtime.getRuntime().exec("su -c echo root")
            val exitCode = process.waitFor()
            exitCode == 0
        } catch (e: Exception) {
            false
        }
    }
    
    companion object {
        private const val TAG = "RemoteControl"
    }
}
```

### 5.4 看门狗模块

#### 5.4.1 PlayerService

```kotlin
@AndroidEntryPoint
class PlayerService : LifecycleService() {
    
    @Inject
    lateinit var syncManager: SyncManager
    
    @Inject
    lateinit var remoteControl: RemoteControl
    
    private val binder = PlayerBinder()
    private var playerActivity: WeakReference<PlayerActivity>? = null
    
    // 看门狗相关
    private val handler = Handler(Looper.getMainLooper())
    private var restartCount = 0
    private var lastRestartTime = 0L
    
    companion object {
        private const val CHECK_INTERVAL = 30_000L  // 30秒
        private const val MAX_RESTART_ATTEMPTS = 5
        private const val RESTART_COOLDOWN = 60_000L  // 1分钟冷却
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "player_service"
    }
    
    inner class PlayerBinder : Binder() {
        fun getService(): PlayerService = this@PlayerService
    }
    
    override fun onBind(intent: Intent): IBinder {
        super.onBind(intent)
        return binder
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification())
        startWatchdog()
    }
    
    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "播放器服务",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "SignBoard 播放器后台服务"
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }
    
    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("SignBoard 播放器")
            .setContentText("正在运行")
            .setSmallIcon(R.drawable.ic_player)
            .setOngoing(true)
            .build()
    }
    
    private fun startWatchdog() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                checkPlayerActivity()
                handler.postDelayed(this, CHECK_INTERVAL)
            }
        }, CHECK_INTERVAL)
    }
    
    private fun checkPlayerActivity() {
        val activity = playerActivity?.get()
        if (activity == null || activity.isFinishing || activity.isDestroyed) {
            Log.w(TAG, "检测到播放器 Activity 已退出")
            restartPlayerActivity()
        }
    }
    
    private fun restartPlayerActivity() {
        val currentTime = System.currentTimeMillis()
        
        // 冷却期检查
        if (currentTime - lastRestartTime < RESTART_COOLDOWN) {
            Log.d(TAG, "冷却期中，跳过重启")
            return
        }
        
        // 最大重启次数检查
        if (restartCount >= MAX_RESTART_ATTEMPTS) {
            Log.w(TAG, "超过最大重启次数，等待冷却期重置")
            restartCount = 0
            return
        }
        
        restartCount++
        lastRestartTime = currentTime
        
        Log.i(TAG, "第 $restartCount 次重启播放器 Activity")
        
        val intent = Intent(this, PlayerActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        startActivity(intent)
    }
    
    fun registerActivity(activity: PlayerActivity) {
        playerActivity = WeakReference(activity)
        restartCount = 0  // Activity 正常连接，重置计数器
    }
    
    fun unregisterActivity() {
        playerActivity = null
    }
    
    fun startSync(displayId: Int, token: String) {
        syncManager.start(displayId, token)
    }
    
    fun stopSync() {
        syncManager.stop()
    }
    
    fun handleCommand(command: String, params: Map<String, Any> = emptyMap()) {
        when (command) {
            "screen_off" -> remoteControl.screenOff()
            "screen_on", "wake_up" -> remoteControl.screenOn()
            "restart" -> {
                // 二次确认由 Activity 处理
                remoteControl.restart()
            }
            "screenshot" -> {
                // 截图逻辑
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        syncManager.stop()
    }
    
    companion object {
        private const val TAG = "PlayerService"
    }
}
```

### 5.5 数据模型

#### 5.5.1 SyncResponse

```kotlin
data class SyncResponse(
    val displayId: Int,
    val currentSchedule: Schedule?,
    val currentLayout: Layout?,
    val mediaList: List<Media>,
    val commands: List<String>,
    val serverTime: String
)

data class Schedule(
    val id: Int,
    val name: String,
    val layoutId: Int,
    val displayIds: List<Int>?,
    val startTime: String?,
    val endTime: String?,
    val priority: Int,
    val isActive: Boolean,
    val repeatType: String?,
    val repeatDays: List<Int>?,
    val repeatStartTime: String?,
    val repeatEndTime: String?,
    val repeatUntil: String?
)

data class Layout(
    val id: Int,
    val name: String,
    val type: String,
    val zones: List<Zone>,
    val marquee: Marquee?,
    val transitionDurationMs: Int,
    val bgmMediaId: Int?,
    val bgmVolume: Int,
    val resolutionWidth: Int,
    val resolutionHeight: Int,
    val createdAt: String,
    val updatedAt: String?
)

data class Zone(
    val mediaId: Int?,
    val x: Float,
    val y: Float,
    val w: Float,
    val h: Float,
    val durationSeconds: Int,
    val volume: Int,
    val fillMode: String,
    val pptMode: String?,
    val pptSlideIndex: Int?,
    // 运行时字段
    var pptImages: List<String>?,
    var _pptSlideIndex: Int = 0
)

data class Marquee(
    val text: String,
    val speed: Int,
    val fontSize: Int,
    val fontColor: String,
    val bgColor: String
)

data class Media(
    val id: Int,
    val name: String,
    val type: String,
    val filePath: String,
    val thumbnailPath: String?,
    val durationSeconds: Int?,
    val fileSize: Int,
    val pptImages: List<String>?,
    val pptSlideDuration: Int,
    val createdAt: String
)
```

---

## 六、API 对接

### 6.1 API 接口定义

```kotlin
interface ApiService {
    
    @POST("displays/register")
    suspend fun register(@Body data: DisplayRegister): Response<DisplayRegisterResponse>
    
    @GET("player/sync/{displayId}")
    suspend fun sync(
        @Path("displayId") displayId: Int,
        @Header("Authorization") token: String
    ): Response<SyncResponse>
    
    @GET("player/download/{path}")
    suspend fun downloadMedia(
        @Path("path") path: String,
        @Header("Authorization") token: String
    ): Response<ResponseBody>
    
    @GET("player/events/{displayId}")
    suspend fun sseEvents(
        @Path("displayId") displayId: Int,
        @Header("Authorization") token: String
    ): Response<ResponseBody>
    
    @POST("displays/{displayId}/heartbeat")
    suspend fun heartbeat(
        @Path("displayId") displayId: Int,
        @Body data: HeartbeatData
    ): Response<Unit>
    
    @POST("displays/{displayId}/screenshot")
    suspend fun uploadScreenshot(
        @Path("displayId") displayId: Int,
        @Body file: RequestBody
    ): Response<Unit>
    
    @POST("displays/{displayId}/command_result")
    suspend fun reportCommandResult(
        @Path("displayId") displayId: Int,
        @Body result: CommandResult
    ): Response<Unit>
}
```

### 6.2 API 客户端

```kotlin
object ApiClient {
    
    private const val BASE_URL = "http://your-server:8000"
    
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()
    
    val apiService: ApiService = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(ApiService::class.java)
}
```

---

## 七、AndroidManifest 配置

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.signboard.player">
    
    <!-- 网络权限 -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    
    <!-- 存储权限 -->
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    
    <!-- 前台服务权限 -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    
    <!-- 屏幕控制权限 -->
    <uses-permission android:name="android.permission.WRITE_SETTINGS" />
    
    <!-- 保持唤醒 -->
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    
    <!-- 开机自启 -->
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    
    <!-- 截图权限（可选） -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
    
    <application
        android:name=".SignBoardApp"
        android:allowBackup="false"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.SignBoard">
        
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="landscape">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <activity
            android:name=".PlayerActivity"
            android:exported="false"
            android:screenOrientation="landscape"
            android:theme="@style/Theme.SignBoard.Fullscreen"
            android:configChanges="orientation|screenSize|keyboardHidden" />
        
        <service
            android:name=".service.PlayerService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="mediaProjection" />
        
        <receiver
            android:name=".BootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
```

---

## 八、打包与分发

### 8.1 打包命令

```bash
# Android Studio
Build → Build Bundle(s) / APK(s) → Build APK(s)

# 命令行
./gradlew assembleRelease
```

### 8.2 输出文件

```
app/build/outputs/apk/
├── debug/
│   └── app-debug.apk        # 调试版（~25MB）
└── release/
    └── app-release.apk      # 正式版（~15MB，混淆后）
```

### 8.3 签名配置

```gradle
android {
    signingConfigs {
        create("release") {
            storeFile = file("keystore.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD") ?: ""
            keyAlias = System.getenv("KEY_ALIAS") ?: ""
            keyPassword = System.getenv("KEY_PASSWORD") ?: ""
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
        }
    }
}
```

### 8.4 分发方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| 直接传输 | 通过 USB/蓝牙/邮件发送 APK | 单设备测试 |
| 内网分发 | 放在 Server 的 `/downloads/` 目录 | 企业内网批量部署 |
| MDM 推送 | 通过企业移动设备管理系统 | 大规模部署 |
| 应用商店 | Google Play / 自建应用商店 | 公开发布 |

---

## 九、开发计划

### 9.1 里程碑

| 阶段 | 内容 | 工作量 | 预计时间 |
|------|------|--------|----------|
| **M1** | 项目骨架 + 注册 + 同步 | 3 天 | 第 1 周 |
| **M2** | 图片播放 + 视频播放 | 3 天 | 第 1-2 周 |
| **M3** | 布局系统 + 走马灯 | 3 天 | 第 2 周 |
| **M4** | 离线缓存 + SSE | 2 天 | 第 2-3 周 |
| **M5** | 控制功能 + 看门狗 | 2 天 | 第 3 周 |
| **M6** | 联调测试 + Bug 修复 | 2 天 | 第 3 周 |
| **合计** | | **15 天** | **3 周** |

### 9.2 详细任务

| 任务 | 依赖 | 产出 |
|------|------|------|
| 项目初始化 | 无 | 空项目 + 依赖配置 |
| API 接口定义 | 无 | ApiService.kt |
| 屏幕注册 | API | MainActivity.kt |
| 排程同步 | 注册 | SyncManager.kt |
| 素材下载 | 同步 | MediaDownloader.kt |
| 图片播放 | 下载 | ImagePlayer.kt |
| 视频播放 | 下载 | VideoPlayer.kt |
| 布局系统 | 播放 | LayoutManager.kt |
| 走马灯 | 布局 | MarqueeView.kt |
| 离线缓存 | 同步 | Room 数据库 |
| SSE 推送 | 同步 | SseClient.kt |
| 熄屏/唤醒 | 无 | RemoteControl.kt |
| 重启控制 | 无 | RemoteControl.kt |
| 前台 Service | 无 | PlayerService.kt |
| 开机自启 | Service | BootReceiver.kt |
| Server 小改 | 无 | schemas.py + display.py |
| 前端小改 | 无 | Displays.vue |
| 联调测试 | 全部 | 测试报告 |

---

## 十、Server 端小改（可选）

### 10.1 新增枚举值

```python
# shared/schemas.py
class PlayerCommand(str, Enum):
    RESTART = "restart"
    SCREENSHOT = "screenshot"
    SCREEN_OFF = "screen_off"      # 新增
    SCREEN_ON = "screen_on"        # 新增
    WAKE_UP = "wake_up"            # 新增
```

### 10.2 前端新增按钮

```vue
<!-- frontend/src/views/Displays.vue -->
<template>
  <!-- 现有按钮 -->
  <button @click="restart(item)" class="...">重启</button>
  
  <!-- 新增按钮 -->
  <button @click="screenOff(item)" class="...">熄屏</button>
  <button @click="screenOn(item)" class="...">唤醒</button>
</template>

<script setup>
async function screenOff(item) {
  if (!confirm(`确定要熄灭「${item.name}」的屏幕吗？`)) return
  try {
    await displayApi.command(item.id, 'screen_off')
    toast.success('熄屏指令已发送')
  } catch (e) {
    toast.error(e.message)
  }
}

async function screenOn(item) {
  if (!confirm(`确定要唤醒「${item.name}」的屏幕吗？`)) return
  try {
    await displayApi.command(item.id, 'screen_on')
    toast.success('唤醒指令已发送')
  } catch (e) {
    toast.error(e.message)
  }
}
</script>
```

---

## 十一、注意事项

### 11.1 安全性

| 风险 | 措施 |
|------|------|
| Root 权限滥用 | 限制 `su` 仅允许 `reboot` 命令 |
| 指令篡改 | 指令增加 HMAC 签名验证 |
| 误操作 | 重启/熄屏/唤醒需二次确认 |

### 11.2 兼容性

| 设备类型 | 支持情况 |
|----------|----------|
| Android 7.0+ | ✅ 完全支持 |
| Android 6.0 | ⚠️ 部分功能受限 |
| Android 5.0 | ❌ 不支持 |
| Root 设备 | ✅ 支持重启 |
| 非 Root 设备 | ⚠️ 仅支持熄屏/唤醒 |

### 11.3 性能优化

| 优化项 | 方案 |
|------|------|
| 图片加载 | Coil 异步加载 + 内存缓存 |
| 视频播放 | ExoPlayer 硬件解码 |
| 网络请求 | OkHttp 连接池 + 缓存 |
| 数据库 | Room 索引优化 |

---

## 十二、附录

### 12.1 参考资料

- [Android 官方文档](https://developer.android.com/)
- [ExoPlayer 文档](https://developer.android.com/guide/topics/media/exoplayer)
- [Coil 文档](https://coil-kt.github.io/coil/)
- [Room 文档](https://developer.android.com/training/data-storage/room)

### 12.2 相关文件

| 文件 | 说明 |
|------|------|
| `docs/开发记录.md` | 开发过程记录 |
| `docs/Android端开发方案.md` | 本文档 |
| `README.md` | 项目说明 |
