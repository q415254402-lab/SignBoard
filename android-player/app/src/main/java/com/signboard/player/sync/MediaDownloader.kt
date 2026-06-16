package com.signboard.player.sync

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit

class MediaDownloader {
    
    companion object {
        private const val TAG = "MediaDownloader"
        
        fun download(url: String, token: String, outputFile: File): Boolean {
            return try {
                Log.d(TAG, "开始下载: $url -> ${outputFile.absolutePath}")
                
                val client = OkHttpClient.Builder()
                    .connectTimeout(30, TimeUnit.SECONDS)
                    .readTimeout(60, TimeUnit.SECONDS)
                    .build()
                
                val request = Request.Builder()
                    .url(url)
                    .addHeader("X-Player-Token", token)
                    .build()
                
                client.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body
                        if (body != null) {
                            outputFile.parentFile?.mkdirs()
                            val bytes = body.byteStream()
                            FileOutputStream(outputFile).use { output ->
                                bytes.copyTo(output)
                            }
                            Log.d(TAG, "下载成功: ${outputFile.name} (${outputFile.length()} bytes)")
                            true
                        } else {
                            Log.e(TAG, "下载失败: 响应体为空")
                            false
                        }
                    } else {
                        Log.e(TAG, "下载失败: HTTP ${response.code} $url")
                        false
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "下载异常: ${url} - ${e.message}")
                false
            }
        }
    }
}
