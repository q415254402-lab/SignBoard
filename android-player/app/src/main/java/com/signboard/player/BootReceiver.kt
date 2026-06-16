package com.signboard.player

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    
    companion object {
        private const val TAG = "BootReceiver"
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == "android.intent.action.LOCKED_BOOT_COMPLETED") {
            
            Log.i(TAG, "设备启动完成")
            
            val prefs = context.getSharedPreferences("signboard", Context.MODE_PRIVATE)
            val displayId = prefs.getInt("display_id", 0)
            val token = prefs.getString("player_token", "")
            
            if (displayId > 0 && !token.isNullOrEmpty()) {
                Log.i(TAG, "有已保存配置，启动播放器 (displayId=$displayId)")
                
                // 启动播放器 Activity
                val activityIntent = Intent(context, PlayerActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                    putExtra("display_id", displayId)
                    putExtra("player_token", token)
                }
                context.startActivity(activityIntent)
            } else {
                Log.i(TAG, "无已保存配置，跳过自动启动")
            }
        }
    }
}
