package com.signboard.player

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import kotlin.math.abs
import com.signboard.player.api.ApiClient
import com.signboard.player.model.SyncResponse
import com.signboard.player.player.LayoutManager
import com.signboard.player.service.PlayerService
import com.signboard.player.sync.ScreenshotManager
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody

class PlayerActivity : AppCompatActivity() {
    
    companion object {
        private const val TAG = "PlayerActivity"
        private const val BACK_PRESS_INTERVAL = 2000L // 2秒内双击退出
        private const val CORNER_TAP_COUNT = 5         // 角落点击次数
        private const val CORNER_TAP_TIMEOUT = 3000L   // 3秒超时
        private const val CORNER_SIZE_DP = 100         // 角落区域大小(dp)
    }
    
    private var container: FrameLayout? = null
    private var loadingView: TextView? = null
    private var layoutManager: LayoutManager? = null

    private var service: PlayerService? = null
    private var displayId: Int = 0
    private var playerToken: String = ""

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var currentLayoutKey: String = ""
    private var isBound = false

    // 退出确认：2秒内双击返回键退出
    private var lastBackPressTime = 0L

    // 角落点击：5次点击进入设置
    private var cornerTapCount = 0
    private var cornerTapFirstTime = 0L
    private val cornerHandler = Handler(Looper.getMainLooper())
    
    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, binder: IBinder) {
            try {
                val playerBinder = binder as PlayerService.PlayerBinder
                service = playerBinder.getService()
                service?.registerActivity(this@PlayerActivity)
                service?.startSync(displayId, playerToken)
                
                scope.launch {
                    service?.getSyncManager()?.scheduleUpdated?.collectLatest { data ->
                        onScheduleUpdated(data)
                    }
                }
                Log.d(TAG, "服务绑定成功")
            } catch (e: Exception) {
                Log.e(TAG, "服务绑定失败", e)
            }
        }
        
        override fun onServiceDisconnected(name: ComponentName) {
            service = null
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        try {
            // 全屏显示 - 先设置 flag，不调用 hideSystemUI
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            
            // setContentView 必须在 hideSystemUI 之前
            setContentView(R.layout.activity_player)
            
            container = findViewById(R.id.container)
            loadingView = findViewById(R.id.loadingView)
            layoutManager = LayoutManager(this)
            
            // 获取参数
            displayId = intent.getIntExtra("display_id", 0)
            playerToken = intent.getStringExtra("player_token") ?: ""
            
            if (displayId == 0) {
                val prefs = getSharedPreferences("signboard", MODE_PRIVATE)
                displayId = prefs.getInt("display_id", 0)
                playerToken = prefs.getString("player_token", "") ?: ""
            }
            
            Log.d(TAG, "启动播放器: displayId=$displayId")
            
            // 现在可以安全地调用 hideSystemUI
            hideSystemUI()

            // 设置角落点击监听（进入设置页面）
            setupCornerTap()

            // 延迟绑定服务
            window.decorView.post {
                bindToService()
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "onCreate 失败", e)
            finish()
        }
    }
    
    private fun bindToService() {
        try {
            val serviceIntent = Intent(this, PlayerService::class.java)
            
            // Android 7.0 直接使用 startService
            startService(serviceIntent)
            
            bindService(serviceIntent, connection, Context.BIND_AUTO_CREATE)
            isBound = true
            Log.d(TAG, "服务绑定请求已发送")
        } catch (e: Exception) {
            Log.e(TAG, "绑定服务失败", e)
            loadingView?.text = "服务启动失败\n请检查应用权限"
        }
    }
    
    private fun onScheduleUpdated(data: SyncResponse) {
        try {
            val layout = data.currentLayout ?: run {
                loadingView?.text = "已连接\n暂无排程"
                loadingView?.visibility = View.VISIBLE
                container?.visibility = View.GONE
                return
            }
            
            val schedule = data.currentSchedule
            val scheduleId = schedule?.id ?: ""
            val layoutKey = "${scheduleId}_${layout.id}_${layout.updatedAt ?: layout.createdAt}"
            
            if (layoutKey == currentLayoutKey) {
                return
            }
            
            currentLayoutKey = layoutKey
            
            val mediaPaths = mutableMapOf<Int, java.io.File>()
            val mediaListMap = mutableMapOf<Int, com.signboard.player.model.Media>()
            
            val cacheDir = java.io.File(cacheDir, "media")
            for (media in data.mediaList) {
                // 即使文件不存在也加入路径，让布局知道素材位置
                val localPath = java.io.File(cacheDir, media.filePath)
                mediaPaths[media.id] = localPath
                mediaListMap[media.id] = media
            }
            
            loadingView?.visibility = View.GONE
            container?.visibility = View.VISIBLE
            layoutManager?.switchLayout(layout, mediaPaths, mediaListMap, container!!)
            
        } catch (e: Exception) {
            Log.e(TAG, "onScheduleUpdated 失败", e)
        }
    }
    
    /**
     * 允许屏幕熄灭（移除 FLAG_KEEP_SCREEN_ON）
     */
    fun allowScreenOff() {
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        Log.d(TAG, "已移除 FLAG_ALLOW_SCREEN_ON，屏幕可熄灭")
    }
    
    /**
     * 禁止屏幕熄灭（添加 FLAG_KEEP_SCREEN_ON）
     */
    fun keepScreenOn() {
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        Log.d(TAG, "已添加 FLAG_KEEP_SCREEN_ON，屏幕保持常亮")
    }
    
    /**
     * 请求截图权限
     */
    fun requestScreenshotPermission() {
        val screenshotManager = ScreenshotManager(this)
        screenshotManager.requestScreenshotPermission(this)
    }
    
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == ScreenshotManager.REQUEST_MEDIA_PROJECTION && resultCode == RESULT_OK) {
            val screenshotManager = ScreenshotManager(this)
            val bitmap = screenshotManager.takeScreenshot(data)
            if (bitmap != null) {
                val file = screenshotManager.saveScreenshot(bitmap, "screenshot_${System.currentTimeMillis()}.jpg")
                if (file != null) {
                    Log.i(TAG, "截图成功: ${file.absolutePath}")
                    // 上传到服务器
                    uploadScreenshot(file)
                }
            } else {
                Toast.makeText(this, "截图失败", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun uploadScreenshot(file: java.io.File) {
        scope.launch(Dispatchers.IO) {
            try {
                val requestBody = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                val multipart = MultipartBody.Part.createFormData("file", file.name, requestBody)
                
                val response = ApiClient.apiService.uploadScreenshot(
                    displayId,
                    multipart,
                    playerToken
                )
                
                withContext(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        Toast.makeText(this@PlayerActivity, "截图已上传", Toast.LENGTH_SHORT).show()
                        Log.i(TAG, "截图上传成功")
                    } else {
                        Toast.makeText(this@PlayerActivity, "截图上传失败: ${response.code()}", Toast.LENGTH_SHORT).show()
                        Log.e(TAG, "截图上传失败: ${response.code()}")
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PlayerActivity, "截图上传异常: ${e.message}", Toast.LENGTH_SHORT).show()
                }
                Log.e(TAG, "截图上传异常", e)
            }
        }
    }
    
    // ── 退出确认：2秒内双击返回键退出 ──

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        val now = System.currentTimeMillis()
        if (now - lastBackPressTime < BACK_PRESS_INTERVAL) {
            // 2秒内双击，退出
            Log.i(TAG, "双击返回键，退出播放器")
            finish()
        } else {
            lastBackPressTime = now
            Toast.makeText(this, "再按一次退出", Toast.LENGTH_SHORT).show()
        }
    }

    // ── 角落点击：5次点击进入设置 ──

    private fun setupCornerTap() {
        val rootLayout = findViewById<com.signboard.player.widget.CornerTapLayout>(R.id.rootLayout) ?: return
        val density = resources.displayMetrics.density
        rootLayout.cornerSizePx = (CORNER_SIZE_DP * density).toInt()
        rootLayout.cornerTapListener = object : com.signboard.player.widget.CornerTapLayout.OnCornerTapListener {
            override fun onCornerTap() {
                handleCornerTap()
            }
        }
    }

    private fun handleCornerTap() {
        val now = System.currentTimeMillis()

        // 超时重置计数
        if (cornerTapCount > 0 && now - cornerTapFirstTime > CORNER_TAP_TIMEOUT) {
            cornerTapCount = 0
        }

        if (cornerTapCount == 0) {
            cornerTapFirstTime = now
        }
        cornerTapCount++

        Log.d(TAG, "角落点击: $cornerTapCount / $CORNER_TAP_COUNT")

        if (cornerTapCount >= CORNER_TAP_COUNT) {
            // 达到5次，进入设置
            cornerTapCount = 0
            Log.i(TAG, "角落点击5次，跳转设置页面")
            val intent = Intent(this, MainActivity::class.java)
            intent.action = "OPEN_SETTINGS"
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            startActivity(intent)
            finish()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            service?.unregisterActivity()
            if (isBound) {
                unbindService(connection)
                isBound = false
            }
            scope.cancel()
            layoutManager?.stop()
        } catch (e: Exception) {
            Log.e(TAG, "onDestroy 失败", e)
        }
    }
    
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            hideSystemUI()
        }
    }
    
    private fun hideSystemUI() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                window.insetsController?.hide(android.view.WindowInsets.Type.systemBars())
            } else {
                @Suppress("DEPRECATION")
                window.decorView.systemUiVisibility = (
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                    View.SYSTEM_UI_FLAG_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "hideSystemUI 失败: ${e.message}")
        }
    }
}
