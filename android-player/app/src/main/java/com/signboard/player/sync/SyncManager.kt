package com.signboard.player.sync

import android.content.Context
import android.util.Log
import com.signboard.player.api.ApiClient
import com.signboard.player.model.ConnectionState
import com.signboard.player.model.Media
import com.signboard.player.model.SyncResponse
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import java.io.File

class SyncManager(private val context: Context) {
    
    companion object {
        private const val TAG = "SyncManager"
        private const val SYNC_INTERVAL = 30_000L  // 30秒
    }
    
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var syncJob: Job? = null
    private var sseJob: Job? = null
    
    // 事件回调
    private val _scheduleUpdated = MutableSharedFlow<SyncResponse>()
    val scheduleUpdated: SharedFlow<SyncResponse> = _scheduleUpdated
    
    private val _connectionChanged = MutableSharedFlow<ConnectionState>()
    val connectionChanged: SharedFlow<ConnectionState> = _connectionChanged
    
    private val _commandReceived = MutableSharedFlow<String>()
    val commandReceived: SharedFlow<String> = _commandReceived
    
    private var displayId: Int = 0
    private var token: String = ""
    
    /**
     * 启动同步
     */
    fun start(displayId: Int, token: String) {
        this.displayId = displayId
        this.token = token
        
        // 首次同步
        scope.launch {
            doSync()
        }
        
        // 启动轮询
        syncJob = scope.launch {
            while (isActive) {
                delay(SYNC_INTERVAL)
                doSync()
            }
        }
        
        // 启动 SSE
        startSse()
        
        // 启动心跳
        startHeartbeat()
    }
    
    /**
     * 停止同步
     */
    fun stop() {
        syncJob?.cancel()
        sseJob?.cancel()
        scope.cancel()
    }
    
    /**
     * 执行同步
     */
    private suspend fun doSync() {
        try {
            _connectionChanged.emit(ConnectionState.CONNECTING)
            
            // 1. 先获取排程数据（IO 线程）
            val data = withContext(Dispatchers.IO) {
                val response = ApiClient.apiService.sync(displayId, token)
                if (response.isSuccessful) {
                    response.body()!!
                } else if (response.code() == 401) {
                    // Token 失效，需要重新注册
                    Log.w(TAG, "Token 失效 (401)，尝试重新注册")
                    withContext(Dispatchers.IO) { reRegister() }
                    throw Exception("Token 已更新，重新同步")
                } else {
                    throw Exception("同步失败: ${response.code()}")
                }
            }
            
            // 2. 下载素材（IO 线程，等待完成）
            withContext(Dispatchers.IO) {
                downloadMedia(data.mediaList)
            }
            
            // 3. 下载完成后再更新 UI
            _connectionChanged.emit(ConnectionState.CONNECTED)
            _scheduleUpdated.emit(data)
            
            // 3.5 同步服务器端修改的设备名称
            data.displayName?.let { newName ->
                val prefs = context.getSharedPreferences("signboard", android.content.Context.MODE_PRIVATE)
                val oldName = prefs.getString("display_name", "")
                if (newName.isNotEmpty() && newName != oldName) {
                    prefs.edit().putString("display_name", newName).apply()
                    Log.i(TAG, "设备名称已同步: $oldName -> $newName")
                }
            }
            
            // 4. 保存同步数据到本地（离线恢复用）
            saveSyncCache(data)
            
            // 5. 处理待执行的指令
            data.commands.forEach { command ->
                Log.d(TAG, "执行指令: $command")
                _commandReceived.emit(command)
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "同步失败", e)
            _connectionChanged.emit(ConnectionState.ERROR)
            tryOfflineFallback()
        }
    }
    
    /**
     * 启动 SSE 监听
     */
    private fun startSse() {
        sseJob = scope.launch {
            val baseUrl = ApiClient.getBaseUrl()
            val url = "${baseUrl}api/v1/player/events/$displayId"
            Log.d(TAG, "SSE URL: $url")
            SseClient.connect(
                url = url,
                token = token,
                onSync = {
                    scope.launch { doSync() }
                },
                onCommand = { command ->
                    Log.d(TAG, "SSE 收到指令: $command")
                    scope.launch { _commandReceived.emit(command) }
                },
                onDisconnected = {
                    Log.d(TAG, "SSE 断开，继续轮询")
                }
            )
        }
    }
    
    /**
     * 启动心跳
     */
    private fun startHeartbeat() {
        scope.launch {
            while (isActive) {
                delay(30_000)  // 30秒
                try {
                    val dm = context.resources.displayMetrics
                    val ip = getLocalIpAddress()
                    val heartbeatData = com.signboard.player.model.HeartbeatData(
                        displayId = displayId,
                        playerVersion = "2.1.0",
                        screenWidth = dm.widthPixels,
                        screenHeight = dm.heightPixels,
                        platform = "android",
                        ipAddress = ip
                    )
                    val response = ApiClient.apiService.heartbeat(displayId, heartbeatData, token)
                    if (response.code() == 401) {
                        Log.w(TAG, "心跳 401，重新注册")
                        reRegister()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "心跳失败", e)
                }
            }
        }
    }
    
    /**
     * 下载素材
     */
    private suspend fun downloadMedia(mediaList: List<Media>) {
        val cacheDir = File(context.cacheDir, "media")
        cacheDir.mkdirs()
        
        for (media in mediaList) {
            val localPath = File(cacheDir, media.filePath)
            if (!localPath.exists()) {
                MediaDownloader.download(
                    url = "${getBaseUrl()}api/v1/player/download/${media.filePath}",
                    token = token,
                    outputFile = localPath
                )
            }
            
            // 下载 PPT 所有图片
            media.pptImages?.forEach { imgPath ->
                val localImgPath = File(cacheDir, imgPath)
                if (!localImgPath.exists()) {
                    MediaDownloader.download(
                        url = "${getBaseUrl()}api/v1/player/download/$imgPath",
                        token = token,
                        outputFile = localImgPath
                    )
                }
            }
        }
    }
    
    /**
     * 保存同步数据到本地
     */
    private fun saveSyncCache(data: com.signboard.player.model.SyncResponse) {
        try {
            val json = com.google.gson.Gson().toJson(data)
            File(context.cacheDir, "last_sync.json").writeText(json)
            Log.d(TAG, "同步数据已保存到缓存")
        } catch (e: Exception) {
            Log.e(TAG, "保存缓存失败", e)
        }
    }
    
    /**
     * 从本地加载同步数据
     */
    private fun loadSyncCache(): com.signboard.player.model.SyncResponse? {
        return try {
            val file = File(context.cacheDir, "last_sync.json")
            if (file.exists()) {
                val json = file.readText()
                com.google.gson.Gson().fromJson(json, com.signboard.player.model.SyncResponse::class.java)
            } else {
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "加载缓存失败", e)
            null
        }
    }
    
    /**
     * 尝试离线回退
     */
    private suspend fun tryOfflineFallback() {
        Log.d(TAG, "尝试离线回退")
        val cached = loadSyncCache()
        if (cached != null) {
            Log.d(TAG, "使用缓存数据")
            _scheduleUpdated.emit(cached)
        } else {
            Log.w(TAG, "无缓存数据")
        }
    }
    
    /**
     * 重新注册（Token 失效时）
     */
    private suspend fun reRegister() {
        for (i in 1..3) {
            try {
                Log.d(TAG, "尝试重新注册 ($i/3)")
                // 获取屏幕分辨率和 IP 地址
                val dm = context.resources.displayMetrics
                val ip = getLocalIpAddress()
                val response = ApiClient.apiService.register(
                    com.signboard.player.model.DisplayRegister(
                        name = context.getSharedPreferences("signboard", android.content.Context.MODE_PRIVATE)
                            .getString("display_name", "Android") ?: "Android",
                        screenWidth = dm.widthPixels,
                        screenHeight = dm.heightPixels,
                        platform = "android",
                        ipAddress = ip
                    )
                )
                if (response.isSuccessful) {
                    val data = response.body()!!
                    displayId = data.id
                    token = data.playerToken ?: ""
                    savePlayerToken(token)
                    Log.i(TAG, "重新注册成功: displayId=$displayId")
                    return
                }
            } catch (e: Exception) {
                Log.e(TAG, "重新注册失败 ($i/3): ${e.message}")
                kotlinx.coroutines.delay(2000L * i)
            }
        }
        Log.e(TAG, "重新注册失败，已达最大重试次数")
    }
    
    /**
     * 保存 player_token
     */
    private fun savePlayerToken(token: String) {
        val prefs = context.getSharedPreferences("signboard", android.content.Context.MODE_PRIVATE)
        prefs.edit().putString("player_token", token).apply()
    }
    
    /**
     * 获取本地 IP 地址
     */
    private fun getLocalIpAddress(): String {
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                val addresses = networkInterface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val address = addresses.nextElement()
                    if (!address.isLoopbackAddress && address is java.net.Inet4Address) {
                        return address.hostAddress ?: ""
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取 IP 地址失败", e)
        }
        return ""
    }
    
    /**
     * 获取本地素材路径
     */
    fun getMediaPath(mediaId: Int, filePath: String): File? {
        val localPath = File(context.cacheDir, "media/$filePath")
        return if (localPath.exists()) localPath else null
    }
    
    private fun getBaseUrl(): String {
        return ApiClient.getBaseUrl()
    }
}
