package com.signboard.player.api

import android.content.Context
import com.signboard.player.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.ResponseBody.Companion.toResponseBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private var _baseUrl = BuildConfig.BASE_URL
    private var appContext: Context? = null

    fun init(context: Context) {
        appContext = context.applicationContext
    }

    fun getBaseUrl(): String {
        // 每次从 SharedPreferences 读取，确保始终用最新的地址
        appContext?.let { ctx ->
            try {
                val saved = ctx.getSharedPreferences("signboard", Context.MODE_PRIVATE)
                    .getString("server_url", "") ?: ""
                if (saved.isNotEmpty()) {
                    val url = if (saved.endsWith("/")) saved else "$saved/"
                    if (url != _baseUrl) {
                        android.util.Log.i("ApiClient", "baseUrl 自动修正: $_baseUrl -> $url")
                        _baseUrl = url
                        retrofit = null
                    }
                    return _baseUrl
                }
            } catch (_: Exception) {}
        }
        return if (_baseUrl.endsWith("/")) _baseUrl else "$_baseUrl/"
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
            response.newBuilder()
                .body(body.toResponseBody(response.body?.contentType()))
                .build()
        }
        .build()

    private var retrofit: Retrofit? = null

    val apiService: ApiService
        get() {
            val url = getBaseUrl()
            if (retrofit == null) {
                android.util.Log.i("ApiClient", "创建 Retrofit: $url")
                retrofit = Retrofit.Builder()
                    .baseUrl(url)
                    .client(okHttpClient)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
            }
            return retrofit!!.create(ApiService::class.java)
        }

    fun updateBaseUrl(url: String) {
        val newUrl = if (url.endsWith("/")) url else "$url/"
        android.util.Log.i("ApiClient", "updateBaseUrl: $_baseUrl -> $newUrl")
        _baseUrl = newUrl
        retrofit = null
    }
}
