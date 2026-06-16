package com.signboard.player.player

import android.content.Context
import android.net.Uri
import android.util.Log
import android.widget.FrameLayout
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.signboard.player.model.Zone
import java.io.File

class VideoPlayer(context: Context) : FrameLayout(context), com.signboard.player.player.PlayerView {
    
    companion object {
        private const val TAG = "VideoPlayer"
    }
    
    private val exoPlayer = ExoPlayer.Builder(context).build()
    private val playerView = PlayerView(context)
    
    init {
        playerView.player = exoPlayer
        addView(playerView, LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT
        ))
        
        // 循环播放
        exoPlayer.repeatMode = Player.REPEAT_MODE_ALL
    }
    
    override fun configure(zones: List<Zone>, mediaPaths: Map<Int, File>, mediaList: Map<Int, com.signboard.player.model.Media>) {
        if (zones.isEmpty()) return
        
        val zone = zones[0]  // 视频播放器只处理第一个 zone
        val mediaId = zone.mediaId ?: return
        val file = mediaPaths[mediaId] ?: return
        
        val mediaItem = MediaItem.fromUri(Uri.fromFile(file))
        exoPlayer.setMediaItem(mediaItem)
        exoPlayer.volume = zone.volume / 100f
    }
    
    override fun start() {
        exoPlayer.prepare()
        exoPlayer.play()
    }
    
    override fun stop() {
        exoPlayer.stop()
        exoPlayer.release()
    }
}
