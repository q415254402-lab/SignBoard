package com.signboard.player.sync

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Environment
import android.util.Log
import java.io.File
import java.io.FileOutputStream

class ScreenshotManager(private val context: Context) {
    
    companion object {
        private const val TAG = "ScreenshotManager"
        const val REQUEST_MEDIA_PROJECTION = 1001
    }
    
    private var mediaProjectionCallback: Any? = null
    
    /**
     * 请求截图权限
     */
    fun requestScreenshotPermission(activity: Activity) {
        try {
            val projectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            val captureIntent = projectionManager.createScreenCaptureIntent()
            activity.startActivityForResult(captureIntent, REQUEST_MEDIA_PROJECTION)
            Log.d(TAG, "已请求截图权限")
        } catch (e: Exception) {
            Log.e(TAG, "请求截图权限失败", e)
        }
    }
    
    /**
     * 截取屏幕
     */
    fun takeScreenshot(data: Intent?): Bitmap? {
        return try {
            val projectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            val projection = projectionManager.getMediaProjection(Activity.RESULT_OK, data ?: return null)
            
            val metrics = context.resources.displayMetrics
            val width = metrics.widthPixels
            val height = metrics.heightPixels
            val density = metrics.densityDpi
            
            val image = android.media.ImageReader.newInstance(width, height, android.graphics.PixelFormat.RGBA_8888, 1)
            
            val virtualDisplay = projection.createVirtualDisplay(
                "Screenshot",
                width, height, density,
                android.view.Display.DEFAULT_DISPLAY,
                image.surface,
                null, null
            )
            
            // 等待截图完成
            Thread.sleep(200)
            
            val imageObj = image.acquireLatestImage()
            if (imageObj != null) {
                val plane = imageObj.planes[0]
                val buffer = plane.buffer
                val pixelStride = plane.pixelStride
                val rowStride = plane.rowStride
                val rowPadding = rowStride - pixelStride * width
                
                val bitmap = Bitmap.createBitmap(
                    width + rowPadding / pixelStride,
                    height,
                    Bitmap.Config.ARGB_8888
                )
                bitmap.copyPixelsFromBuffer(buffer)
                
                // 裁剪到正确尺寸
                val croppedBitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height)
                if (croppedBitmap != bitmap) {
                    bitmap.recycle()
                }
                
                imageObj.close()
                virtualDisplay?.release()
                image.close()
                
                croppedBitmap
            } else {
                virtualDisplay?.release()
                image.close()
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "截图失败", e)
            null
        }
    }
    
    /**
     * 保存截图到文件
     */
    fun saveScreenshot(bitmap: Bitmap, filename: String): File? {
        return try {
            val dir = File(context.filesDir, "screenshots")
            dir.mkdirs()
            val file = File(dir, filename)
            FileOutputStream(file).use { out ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 85, out)
            }
            Log.d(TAG, "截图已保存: ${file.absolutePath}")
            file
        } catch (e: Exception) {
            Log.e(TAG, "保存截图失败", e)
            null
        }
    }
}
