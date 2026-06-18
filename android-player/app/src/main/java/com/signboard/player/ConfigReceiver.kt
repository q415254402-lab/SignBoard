package com.signboard.player

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Toast
import com.signboard.player.api.ApiClient
import com.signboard.player.model.DisplayRegister
import kotlinx.coroutines.*

/**
 * 接收 ADB 广播修改配置 / 控制播放器
 *
 * 修改配置并启动播放器（全自动：写配置→注册→启动）：
 * adb shell am broadcast -a com.signboard.player.CONFIG_CHANGE \
 *   --es server_url "http://192.168.1.100:8000" \
 *   --es display_name "一楼大厅" \
 *   --ez auto_start true \
 *   com.signboard.player/.ConfigReceiver
 *
 * 仅启动播放器（不改配置）：
 * adb shell am broadcast -a com.signboard.player.START_PLAYER \
 *   com.signboard.player/.ConfigReceiver
 *
 * 清除配置：
 * adb shell am broadcast -a com.signboard.player.CONFIG_CLEAR \
 *   com.signboard.player/.ConfigReceiver
 */
class ConfigReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "ConfigReceiver"
        const val ACTION_CONFIG_CHANGE = "com.signboard.player.CONFIG_CHANGE"
        const val ACTION_CONFIG_CLEAR = "com.signboard.player.CONFIG_CLEAR"
        const val ACTION_START_PLAYER = "com.signboard.player.START_PLAYER"
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onReceive(context: Context, intent: Intent) {
        Log.i(TAG, "=== 收到广播: ${intent.action} ===")

        when (intent.action) {
            ACTION_CONFIG_CHANGE -> {
                val prefs = context.getSharedPreferences("signboard", Context.MODE_PRIVATE)
                val editor = prefs.edit()

                val serverUrl = intent.getStringExtra("server_url")
                val displayName = intent.getStringExtra("display_name") ?: "Android 屏幕"
                val autoStart = intent.getBooleanExtra("auto_start", false)

                if (serverUrl != null) {
                    editor.putString("server_url", serverUrl)
                }
                editor.putString("display_name", displayName)
                editor.commit()

                Log.i(TAG, "配置已写入: url=$serverUrl, name=$displayName, autoStart=$autoStart")
                Toast.makeText(context, "配置已更新", Toast.LENGTH_SHORT).show()

                if (autoStart) {
                    val url = serverUrl ?: prefs.getString("server_url", "")
                    if (url.isNullOrEmpty()) {
                        Log.e(TAG, "服务器地址为空，无法启动")
                        return
                    }
                    autoStartPlayer(context, url, displayName)
                }
            }

            ACTION_CONFIG_CLEAR -> {
                val prefs = context.getSharedPreferences("signboard", Context.MODE_PRIVATE)
                prefs.edit().clear().commit()
                Toast.makeText(context, "配置已清除", Toast.LENGTH_SHORT).show()
            }

            ACTION_START_PLAYER -> {
                val prefs = context.getSharedPreferences("signboard", Context.MODE_PRIVATE)
                val url = prefs.getString("server_url", "") ?: ""
                val name = prefs.getString("display_name", "Android 屏幕") ?: "Android 屏幕"
                if (url.isNotEmpty()) {
                    autoStartPlayer(context, url, name)
                } else {
                    Log.e(TAG, "未配置服务器地址")
                }
            }
        }
    }

    private fun getMacAddress(): String {
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val iface = interfaces.nextElement()
                if (iface.isLoopback || !iface.isUp) continue
                val mac = iface.hardwareAddress
                if (mac != null) {
                    return mac.joinToString(":") { String.format("%02X", it) }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取 MAC 地址失败: ${e.message}")
        }
        return ""
    }

    private fun autoStartPlayer(context: Context, serverUrl: String, displayName: String) {
        Log.i(TAG, "自动启动: 注册服务器...")

        scope.launch {
            try {
                ApiClient.updateBaseUrl(serverUrl)

                val prefs = context.getSharedPreferences("signboard", Context.MODE_PRIVATE)
                var displayId = prefs.getInt("display_id", 0)
                var playerToken = prefs.getString("player_token", "") ?: ""

                // MAC 地址去重（与 MainActivity 同样的方法）
                val mac = getMacAddress()
                Log.i(TAG, "注册/更新设备: name=$displayName, mac=$mac")
                val registerData = DisplayRegister(
                    name = displayName,
                    platform = "android",
                    screenWidth = 0,
                    screenHeight = 0,
                    macAddress = mac.ifEmpty { null }
                )
                val response = ApiClient.apiService.register(registerData)

                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null) {
                        displayId = body.id
                        playerToken = body.playerToken ?: ""

                        prefs.edit()
                            .putInt("display_id", displayId)
                            .putString("player_token", playerToken)
                            .commit()

                        Log.i(TAG, "注册成功: displayId=$displayId")
                    }
                } else {
                    Log.e(TAG, "注册失败: ${response.code()}")
                    withContext(Dispatchers.Main) {
                        Toast.makeText(context, "注册失败: ${response.code()}", Toast.LENGTH_LONG).show()
                    }
                    return@launch
                }

                // 启动播放器
                withContext(Dispatchers.Main) {
                    val intent = Intent(context, PlayerActivity::class.java).apply {
                        putExtra("display_id", displayId)
                        putExtra("player_token", playerToken)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                    }
                    context.startActivity(intent)
                    Log.i(TAG, "播放器已启动: displayId=$displayId")
                }

            } catch (e: Exception) {
                Log.e(TAG, "自动启动失败: ${e.message}", e)
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "启动失败: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}
