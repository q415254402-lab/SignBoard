package com.signboard.player.api

import com.signboard.player.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.ResponseBody.Companion.toResponseBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    
    private var baseUrl = BuildConfig.BASE_URL
    
    fun getBaseUrl(): String {
        // 始终返回带尾部斜杠的 URL（Retrofit 和手动拼接都需要）
        return if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
    }
    
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val request = chain.request()
            android.util.Log.d("ApiClient", "Request: ${request.method} ${request.url}")
            val response = chain.proceed(request)
            val body = response.body?.string() ?: ""
            android.util.Log.d("ApiClient", "Response: ${response.code} ${response.headers["Content-Type"]}")
            android.util.Log.d("ApiClient", "Body: ${body.take(500)}")
            // 重建 response，因为 body 已经被消费
            response.newBuilder()
                .body(body.toResponseBody(response.body?.contentType()))
                .build()
        }
        .build()
    
    private var retrofit: Retrofit? = null
    
    val apiService: ApiService
        get() {
            if (retrofit == null) {
                // 确保 baseUrl 以 / 结尾
                val url = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
                android.util.Log.d("ApiClient", "Base URL: $url")
                retrofit = Retrofit.Builder()
                    .baseUrl(url)
                    .client(okHttpClient)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
            }
            return retrofit!!.create(ApiService::class.java)
        }
    
    fun updateBaseUrl(url: String) {
        // 确保 baseUrl 以 / 结尾
        baseUrl = if (url.endsWith("/")) url else "$url/"
        retrofit = null  // 重建 Retrofit 实例
    }
}
