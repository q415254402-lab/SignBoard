package com.signboard.player.player

import android.view.View
import com.signboard.player.model.Zone

/**
 * 播放器视图接口
 */
interface PlayerView {
    /**
     * 开始播放
     */
    fun start()
    
    /**
     * 停止播放
     */
    fun stop()
    
    /**
     * 配置播放器
     */
    fun configure(zones: List<Zone>, mediaPaths: Map<Int, java.io.File>, mediaList: Map<Int, com.signboard.player.model.Media>)
}
