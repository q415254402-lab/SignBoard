package com.signboard.player.player

import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import android.widget.FrameLayout
import android.widget.ImageView
import com.signboard.player.model.Media
import com.signboard.player.model.Zone
import kotlinx.coroutines.*
import java.io.File

class ImagePlayer(context: Context) : FrameLayout(context), PlayerView {

    companion object {
        private const val TAG = "ImagePlayer"
    }

    private val imageView = ImageView(context)
    private var zones: List<Zone> = emptyList()
    private var mediaPaths: Map<Int, File> = emptyMap()
    private var mediaList: Map<Int, Media> = emptyMap()
    private var currentIndex = 0
    private var timerJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    init {
        addView(imageView, LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT
        ))
        imageView.scaleType = ImageView.ScaleType.FIT_CENTER
        imageView.setBackgroundColor(0xFF000000.toInt())
    }

    override fun configure(zones: List<Zone>, mediaPaths: Map<Int, File>, mediaList: Map<Int, Media>) {
        this.zones = zones
        this.mediaPaths = mediaPaths
        this.mediaList = mediaList
        this.currentIndex = 0
    }

    override fun start() {
        showCurrent()
    }

    override fun stop() {
        timerJob?.cancel()
        scope.cancel()
    }

    private fun showCurrent() {
        if (zones.isEmpty()) return

        val zone = zones[currentIndex]
        val mediaId = zone.mediaId ?: return
        val file = mediaPaths[mediaId] ?: return

        val mediaInfo = mediaList[mediaId]
        if (mediaInfo?.pptImages != null && zone.pptImages == null) {
            zone.pptImages = mediaInfo.pptImages
        }

        val pptMode = zone.pptMode
        val pptImages = zone.pptImages
        val actualFile = if (pptImages != null && pptMode == "fixed") {
            val slideIndex = zone.pptSlideIndex ?: 0
            getPptSlideFile(mediaId, pptImages, slideIndex) ?: file
        } else if (pptImages != null && pptMode != "fixed") {
            val currentSlide = zone._pptSlideIndex
            getPptSlideFile(mediaId, pptImages, currentSlide) ?: file
        } else {
            file
        }

        imageView.scaleType = when (zone.fillMode) {
            "fill" -> ImageView.ScaleType.CENTER_CROP
            "stretch" -> ImageView.ScaleType.FIT_XY
            else -> ImageView.ScaleType.FIT_CENTER
        }

        // 异步加载图片
        scope.launch(Dispatchers.IO) {
            try {
                if (actualFile.exists() && actualFile.length() > 0) {
                    Log.d(TAG, "文件大小: ${actualFile.length()} bytes")
                    
                    // 先检查文件头，判断是否是有效图片
                    val options = BitmapFactory.Options().apply {
                        inJustDecodeBounds = true
                    }
                    BitmapFactory.decodeFile(actualFile.absolutePath, options)
                    
                    if (options.outWidth > 0 && options.outHeight > 0) {
                        Log.d(TAG, "图片尺寸: ${options.outWidth}x${options.outHeight}")
                        
                        // 计算采样率，避免大图片 OOM
                        val sampleSize = calculateSampleSize(options.outWidth, options.outHeight, 1920, 1080)
                        val decodeOptions = BitmapFactory.Options().apply {
                            inSampleSize = sampleSize
                        }
                        val bitmap = BitmapFactory.decodeFile(actualFile.absolutePath, decodeOptions)
                        
                        withContext(Dispatchers.Main) {
                            if (bitmap != null) {
                                imageView.setImageBitmap(bitmap)
                                Log.d(TAG, "图片加载成功: ${actualFile.name} (${bitmap.width}x${bitmap.height})")
                            } else {
                                Log.e(TAG, "图片解码失败: ${actualFile.name}")
                            }
                        }
                    } else {
                        Log.e(TAG, "无效图片文件: ${actualFile.name} (${options.outWidth}x${options.outHeight})")
                        // 文件存在但不是有效图片，可能是下载不完整
                        // 删除并重新下载
                        actualFile.delete()
                        delay(3000)
                        withContext(Dispatchers.Main) {
                            showCurrent()
                        }
                    }
                } else {
                    Log.w(TAG, "文件不存在或为空: ${actualFile.absolutePath}")
                    delay(3000)
                    withContext(Dispatchers.Main) {
                        showCurrent()
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "加载图片异常: ${e.message}")
            }
        }

        val duration = zone.durationSeconds * 1000L
        timerJob = scope.launch {
            delay(duration)
            next()
        }
    }

    private fun getPptSlideFile(mediaId: Int, pptImages: List<String>, slideIndex: Int): File? {
        if (slideIndex >= pptImages.size) return null
        val slidePath = pptImages[slideIndex]
        return mediaPaths[mediaId]?.parentFile?.let { parent ->
            File(parent, slidePath.split("/").last())
        }
    }

    private fun calculateSampleSize(width: Int, height: Int, reqWidth: Int, reqHeight: Int): Int {
        var sampleSize = 1
        if (width > reqWidth || height > reqHeight) {
            val halfWidth = width / 2
            val halfHeight = height / 2
            while (halfWidth / sampleSize >= reqWidth && halfHeight / sampleSize >= reqHeight) {
                sampleSize *= 2
            }
        }
        return sampleSize
    }

    private fun next() {
        val zone = zones[currentIndex]
        val pptImages = zone.pptImages
        if (pptImages != null && zone.pptMode != "fixed") {
            val currentSlide = zone._pptSlideIndex
            if (currentSlide < pptImages.size - 1) {
                zone._pptSlideIndex = currentSlide + 1
            } else {
                zone._pptSlideIndex = 0
                currentIndex = (currentIndex + 1) % zones.size
            }
        } else {
            currentIndex = (currentIndex + 1) % zones.size
        }
        showCurrent()
    }
}
