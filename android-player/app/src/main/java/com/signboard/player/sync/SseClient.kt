package com.signboard.player.sync

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.BufferedReader
import java.io.IOException
import java.util.concurrent.TimeUnit

class SseClient {
    
    companion object {
        private const val TAG = "SseClient"
        
        /**
         * 连接 SSE 长连接
         * @param url SSE 端点 URL
         * @param token Player Token
         * @param onSync 收到同步事件时的回调
         * @param onCommand 收到命令事件时的回调
         * @param onDisconnected 连接断开时的回调
         */
        suspend fun connect(
            url: String,
            token: String,
            onSync: () -> Unit,
            onCommand: (String) -> Unit,
            onDisconnected: () -> Unit
        ) {
            val client = OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .build()
            
            val request = Request.Builder()
                .url(url)
                .addHeader("X-Player-Token", token)
                .build()
            
            var backoff = 1000L
            
            while (true) {
                try {
                    client.newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            backoff = 1000L
                            Log.i(TAG, "SSE 连接成功")
                            
                            var eventType = ""
                            
                            response.body?.byteStream()?.bufferedReader()?.forEachLine { line ->
                                when {
                                    line.startsWith("event:") -> {
                                        eventType = line.substringAfter("event:").trim()
                                    }
                                    line.startsWith("data:") -> {
                                        val data = line.substringAfter("data:").trim()
                                        when (eventType) {
                                            "command" -> {
                                                Log.d(TAG, "收到命令: $data")
                                                // 解析命令 JSON
                                                try {
                                                    val json = org.json.JSONObject(data)
                                                    val command = json.getString("command")
                                                    onCommand(command)
                                                } catch (e: Exception) {
                                                    Log.e(TAG, "解析命令失败: $data", e)
                                                }
                                            }
                                            "connected" -> {
                                                Log.d(TAG, "SSE 已连接: $data")
                                            }
                                            else -> {
                                                // 同步事件
                                                onSync()
                                            }
                                        }
                                        eventType = ""  // 重置事件类型
                                    }
                                }
                            }
                        } else {
                            Log.w(TAG, "SSE 连接失败: ${response.code}")
                        }
                    }
                } catch (e: IOException) {
                    Log.e(TAG, "SSE 连接异常: ${e.message}")
                } catch (e: Exception) {
                    Log.e(TAG, "SSE 未知异常", e)
                }
                
                onDisconnected()
                
                Log.d(TAG, "SSE 重连等待 ${backoff}ms")
                Thread.sleep(backoff)
                backoff = minOf(backoff * 2, 60_000L)
            }
        }
    }
}
