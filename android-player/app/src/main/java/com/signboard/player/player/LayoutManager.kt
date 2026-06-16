package com.signboard.player.player

import android.content.Context
import android.util.Log
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.LinearLayout
import com.signboard.player.model.Layout
import com.signboard.player.model.Marquee
import com.signboard.player.model.Media
import com.signboard.player.model.Zone
import java.io.File

class LayoutManager(private val context: Context) {
    
    companion object {
        private const val TAG = "LayoutManager"
    }
    
    private var currentLayout: Layout? = null
    private var currentWidget: View? = null
    
    /**
     * 切换布局
     */
    fun switchLayout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>,
        container: ViewGroup
    ) {
        Log.i(TAG, "切换布局: ${layout.name} (${layout.type})")
        
        // 清除旧布局
        currentWidget?.let {
            (it as? com.signboard.player.player.PlayerView)?.stop()
            container.removeView(it)
        }
        
        // 根据类型创建新布局
        currentLayout = layout
        currentWidget = when (layout.type) {
            "fullscreen" -> createFullscreenLayout(layout, mediaPaths, mediaList)
            "playlist" -> createPlaylistLayout(layout, mediaPaths, mediaList)
            "split_2" -> createSplit2Layout(layout, mediaPaths, mediaList)
            "split_3" -> createSplit3Layout(layout, mediaPaths, mediaList)
            else -> {
                Log.e(TAG, "未知布局类型: ${layout.type}")
                null
            }
        }
        
        currentWidget?.let {
            container.addView(it, FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            ))
            (it as? com.signboard.player.player.PlayerView)?.start()
        }
    }
    
    private fun createFullscreenLayout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        // 检查第一个 zone 是否是视频
        val firstZone = layout.zones.firstOrNull()
        val mediaId = firstZone?.mediaId
        val media = mediaId?.let { mediaList[it] }
        
        return if (media?.type == "video") {
            VideoPlayer(context).apply {
                configure(layout.zones, mediaPaths, mediaList)
            }
        } else {
            ImagePlayer(context).apply {
                configure(layout.zones, mediaPaths, mediaList)
            }
        }
    }
    
    private fun createPlaylistLayout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        return ImagePlayer(context).apply {
            configure(layout.zones, mediaPaths, mediaList)
        }
    }
    
    private fun createSplit2Layout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        val container = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        
        for ((index, zone) in layout.zones.withIndex()) {
            val zoneContainer = FrameLayout(context).apply {
                val params = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT)
                params.weight = zone.w
                layoutParams = params
            }
            
            val mediaId = zone.mediaId
            val media = mediaId?.let { mediaList[it] }
            
            val playerView = if (media?.type == "video") {
                VideoPlayer(context).apply {
                    configure(listOf(zone), mediaPaths, mediaList)
                }
            } else {
                ImagePlayer(context).apply {
                    configure(listOf(zone), mediaPaths, mediaList)
                }
            }
            
            zoneContainer.addView(playerView, FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            ))
            
            container.addView(zoneContainer)
        }
        
        return container
    }
    
    private fun createSplit3Layout(
        layout: Layout,
        mediaPaths: Map<Int, File>,
        mediaList: Map<Int, Media>
    ): View {
        val container = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
        }
        
        for ((index, zone) in layout.zones.withIndex()) {
            val zoneContainer = FrameLayout(context).apply {
                val params = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0)
                params.weight = zone.h
                layoutParams = params
            }
            
            val mediaId = zone.mediaId
            val media = mediaId?.let { mediaList[it] }
            
            val playerView = if (media?.type == "video") {
                VideoPlayer(context).apply {
                    configure(listOf(zone), mediaPaths, mediaList)
                }
            } else {
                ImagePlayer(context).apply {
                    configure(listOf(zone), mediaPaths, mediaList)
                }
            }
            
            zoneContainer.addView(playerView, FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            ))
            
            container.addView(zoneContainer)
        }
        
        // 添加走马灯（如果有）
        layout.marquee?.let { marquee ->
            val marqueeView = MarqueeView(context).apply {
                configure(marquee)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    60  // 固定高度 60dp
                )
                layoutParams = params
            }
            container.addView(marqueeView)
        }
        
        return container
    }
    
    /**
     * 停止播放
     */
    fun stop() {
        (currentWidget as? com.signboard.player.player.PlayerView)?.stop()
    }
}
