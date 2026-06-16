package com.signboard.player.control

import android.content.Context
import android.net.wifi.WifiManager
import android.os.PowerManager
import android.util.Log

class RemoteControl(private val context: Context) {
    
    companion object {
        private const val TAG = "RemoteControl"
    }
    
    private var isScreenOff = false
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null
    private var savedScreenTimeout: Int = -1  // 保存原始屏幕超时
    
    /**
     * 熄屏
     */
    fun screenOff(): Boolean {
        if (isScreenOff) {
            Log.d(TAG, "屏幕已熄灭，跳过")
            return true
        }
        
        // 方案1：Root + input keyevent 26（立即熄屏）
        if (execSu("input keyevent 26")) {
            isScreenOff = true
            Log.i(TAG, "屏幕已熄灭（Root）")
            return true
        }
        
        // 方案2：降级到设置屏幕超时
        if (android.provider.Settings.System.canWrite(context)) {
            try {
                // 保存原始超时
                savedScreenTimeout = android.provider.Settings.System.getInt(
                    context.contentResolver,
                    android.provider.Settings.System.SCREEN_OFF_TIMEOUT
                )
                android.provider.Settings.System.putInt(
                    context.contentResolver,
                    android.provider.Settings.System.SCREEN_OFF_TIMEOUT, 1000
                )
                isScreenOff = true
                Log.i(TAG, "屏幕已熄灭（超时模式，原始超时=${savedScreenTimeout}ms）")
                return true
            } catch (e: Exception) {
                Log.e(TAG, "熄屏失败", e)
            }
        }
        
        Log.e(TAG, "熄屏失败：无 Root 权限且无 WRITE_SETTINGS 权限")
        return false
    }
    
    /**
     * 唤醒
     */
    fun screenOn(): Boolean {
        if (!isScreenOff) {
            Log.d(TAG, "屏幕未熄灭，跳过唤醒")
            return true
        }
        
        // 方案1：Root + input keyevent 224（立即唤醒）
        if (execSu("input keyevent 224")) {
            isScreenOff = false
            Log.i(TAG, "屏幕已唤醒（Root）")
            return true
        }
        
        // 方案2：降级到 PowerManager
        try {
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            @Suppress("DEPRECATION")
            val wakeLock = powerManager.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP,
                "signboard:wakeup"
            )
            wakeLock.acquire(3000)

            // 恢复屏幕超时为"从不"
            if (android.provider.Settings.System.canWrite(context) && savedScreenTimeout > 0) {
                android.provider.Settings.System.putInt(
                    context.contentResolver,
                    android.provider.Settings.System.SCREEN_OFF_TIMEOUT,
                    savedScreenTimeout
                )
                Log.i(TAG, "屏幕超时已恢复为 ${savedScreenTimeout}ms")
            } else {
                // 无法恢复原始值，设为"从不"（Integer.MAX_VALUE）
                android.provider.Settings.System.putInt(
                    context.contentResolver,
                    android.provider.Settings.System.SCREEN_OFF_TIMEOUT,
                    Int.MAX_VALUE
                )
                Log.i(TAG, "屏幕超时已设为从不")
            }

            isScreenOff = false
            Log.i(TAG, "屏幕已唤醒（WakeLock）")
            return true
        } catch (e: Exception) {
            Log.e(TAG, "唤醒失败", e)
        }
        
        return false
    }
    
    /**
     * 重启系统
     */
    fun restart(): Boolean {
        return if (execSu("reboot")) {
            Log.i(TAG, "重启指令已执行")
            true
        } else {
            Log.e(TAG, "重启失败：Root 不可用")
            false
        }
    }
    
    /**
     * 获取网络锁（防止熄屏后断网）
     * 在 Service 启动时调用
     */
    fun acquireNetworkLock() {
        try {
            // 1. 保持 CPU 运行（防止深度休眠）
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            @Suppress("DEPRECATION")
            wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "signboard:network"
            )
            wakeLock?.acquire()
            Log.i(TAG, "WakeLock 已获取")
            
            // 2. 保持 WiFi 连接（防止熄屏后断 WiFi）
            val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            @Suppress("DEPRECATION")
            wifiLock = wifiManager.createWifiLock(
                WifiManager.WIFI_MODE_FULL_HIGH_PERF,
                "signboard:wifi"
            )
            wifiLock?.acquire()
            Log.i(TAG, "WifiLock 已获取")
            
        } catch (e: Exception) {
            Log.e(TAG, "获取网络锁失败", e)
        }
    }
    
    /**
     * 释放网络锁
     * 在 Service 停止时调用
     */
    fun releaseNetworkLock() {
        try {
            wakeLock?.let {
                if (it.isHeld) {
                    it.release()
                    Log.i(TAG, "WakeLock 已释放")
                }
            }
            wakeLock = null
            
            wifiLock?.let {
                if (it.isHeld) {
                    it.release()
                    Log.i(TAG, "WifiLock 已释放")
                }
            }
            wifiLock = null
        } catch (e: Exception) {
            Log.e(TAG, "释放网络锁失败", e)
        }
    }
    
    /**
     * 执行 Root 命令
     */
    private fun execSu(command: String): Boolean {
        return try {
            val process = Runtime.getRuntime().exec(arrayOf("su", "-c", command))
            val exitCode = process.waitFor()
            if (exitCode == 0) {
                Log.d(TAG, "Root 命令成功: $command")
                true
            } else {
                Log.w(TAG, "Root 命令失败: $command, exit code: $exitCode")
                false
            }
        } catch (e: Exception) {
            Log.w(TAG, "Root 不可用: ${e.message}")
            false
        }
    }
    
    /**
     * 检查 Root 是否可用
     */
    fun isRootAvailable(): Boolean {
        return execSu("echo root")
    }
}
