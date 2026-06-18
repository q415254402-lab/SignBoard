package com.signboard.player

import android.app.Application
import android.util.Log
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.*

class SignBoardApp : Application() {
    
    override fun onCreate() {
        super.onCreate()
        
        // 设置全局未捕获异常处理器
        val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, exception ->
            val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
            val logMessage = """
                |=== CRASH at $timestamp ===
                |Thread: ${thread.name}
                |Exception: ${exception.javaClass.name}
                |Message: ${exception.message}
                |Stack Trace:
                |${exception.stackTraceToString()}
                |===========================
            """.trimMargin()
            
            // 写入文件
            try {
                val logFile = File(filesDir, "crash.log")
                FileWriter(logFile, true).use { writer ->
                    writer.write(logMessage)
                    writer.write("\n\n")
                }
                Log.e("SignBoardApp", logMessage)
            } catch (e: Exception) {
                Log.e("SignBoardApp", "无法写入崩溃日志", e)
            }
            
            // 调用默认处理器
            defaultHandler?.uncaughtException(thread, exception)
        }
        
        com.signboard.player.api.ApiClient.init(this)
        Log.d("SignBoardApp", "应用启动")
    }
}
