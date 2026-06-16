package com.signboard.player.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Binder
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import com.signboard.player.PlayerActivity
import com.signboard.player.R
import com.signboard.player.control.RemoteControl
import com.signboard.player.model.ConnectionState
import com.signboard.player.model.SyncResponse
import com.signboard.player.sync.SyncManager
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest
import java.lang.ref.WeakReference

class PlayerService : Service() {
    
    companion object {
        private const val TAG = "PlayerService"
        private const val CHECK_INTERVAL = 30_000L  // 30秒
        private const val MAX_RESTART_ATTEMPTS = 5
        private const val RESTART_COOLDOWN = 60_000L  // 1分钟冷却
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "player_service"
    }
    
    inner class PlayerBinder : Binder() {
        fun getService(): PlayerService = this@PlayerService
    }
    
    private val binder = PlayerBinder()
    private var playerActivity: WeakReference<PlayerActivity>? = null
    
    // 看门狗相关
    private val handler = Handler(Looper.getMainLooper())
    private var restartCount = 0
    private var lastRestartTime = 0L
    
    // 组件
    private lateinit var syncManager: SyncManager
    private lateinit var remoteControl: RemoteControl
    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    override fun onBind(intent: Intent): IBinder = binder
    
    override fun onCreate() {
        super.onCreate()
        
        try {
            Log.d(TAG, "PlayerService onCreate")
            
            syncManager = SyncManager(this)
            remoteControl = RemoteControl(this)
            
            // 获取网络锁，防止熄屏后断网
            remoteControl.acquireNetworkLock()
            
            startWatchdog()
            
            serviceScope.launch {
                syncManager.connectionChanged.collectLatest { state ->
                    Log.d(TAG, "连接状态: $state")
                }
            }
            
            serviceScope.launch {
                syncManager.scheduleUpdated.collectLatest { data ->
                    Log.d(TAG, "排程更新: ${data.currentLayout?.name}")
                }
            }
            
            // 监听指令
            serviceScope.launch {
                syncManager.commandReceived.collectLatest { command ->
                    Log.d(TAG, "收到指令: $command")
                    handleCommand(command)
                }
            }
            
            Log.d(TAG, "PlayerService 初始化完成")
        } catch (e: Exception) {
            Log.e(TAG, "PlayerService onCreate 失败", e)
        }
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
        val intent = Intent(this, PlayerActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("SignBoard 播放器")
            .setContentText("正在运行")
            .setSmallIcon(R.drawable.ic_player)
            .setContentIntent(pendingIntent)
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
    
    fun handleCommand(command: String) {
        when (command) {
            "screen_off" -> {
                playerActivity?.get()?.allowScreenOff()
                remoteControl.screenOff()
            }
            "screen_on", "wake_up" -> {
                playerActivity?.get()?.keepScreenOn()
                remoteControl.screenOn()
            }
            "restart" -> {
                if (remoteControl.isRootAvailable()) {
                    remoteControl.restart()
                } else {
                    Log.w(TAG, "重启失败：设备没有 Root 权限")
                }
            }
            "screenshot" -> {
                Log.i(TAG, "收到截图指令")
                // 截图功能需要 MediaProjection 权限，由 Activity 处理
                playerActivity?.get()?.requestScreenshotPermission()
            }
        }
    }
    
    fun getSyncManager(): SyncManager = syncManager
    
    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        remoteControl.releaseNetworkLock()
        syncManager.stop()
        serviceScope.cancel()
    }
}
