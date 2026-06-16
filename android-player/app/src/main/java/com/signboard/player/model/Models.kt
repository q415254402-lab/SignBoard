package com.signboard.player.model

import com.google.gson.annotations.SerializedName

data class SyncResponse(
    @SerializedName("display_id") val displayId: Int,
    @SerializedName("display_name") val displayName: String? = null,
    @SerializedName("current_schedule") val currentSchedule: Schedule?,
    @SerializedName("current_layout") val currentLayout: Layout?,
    @SerializedName("media_list") val mediaList: List<Media>,
    val commands: List<String>,
    @SerializedName("server_time") val serverTime: String
)

data class Schedule(
    val id: Int,
    val name: String,
    @SerializedName("layout_id") val layoutId: Int,
    @SerializedName("display_ids") val displayIds: List<Int>?,
    @SerializedName("start_time") val startTime: String?,
    @SerializedName("end_time") val endTime: String?,
    val priority: Int,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("repeat_type") val repeatType: String?,
    @SerializedName("repeat_days") val repeatDays: List<Int>?,
    @SerializedName("repeat_start_time") val repeatStartTime: String?,
    @SerializedName("repeat_end_time") val repeatEndTime: String?,
    @SerializedName("repeat_until") val repeatUntil: String?
)

data class Layout(
    val id: Int,
    val name: String,
    val type: String,
    val zones: List<Zone>,
    val marquee: Marquee?,
    @SerializedName("transition_duration_ms") val transitionDurationMs: Int,
    @SerializedName("bgm_media_id") val bgmMediaId: Int?,
    @SerializedName("bgm_volume") val bgmVolume: Int,
    @SerializedName("resolution_width") val resolutionWidth: Int,
    @SerializedName("resolution_height") val resolutionHeight: Int,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String?
)

data class Zone(
    @SerializedName("media_id") val mediaId: Int?,
    val x: Float,
    val y: Float,
    val w: Float,
    val h: Float,
    @SerializedName("duration_seconds") val durationSeconds: Int,
    val volume: Int,
    @SerializedName("fill_mode") val fillMode: String,
    @SerializedName("ppt_mode") val pptMode: String?,
    @SerializedName("ppt_slide_index") val pptSlideIndex: Int?,
    // 运行时字段
    @Transient var pptImages: List<String>? = null,
    @Transient var _pptSlideIndex: Int = 0
)

data class Marquee(
    val text: String,
    val speed: Int,
    @SerializedName("font_size") val fontSize: Int,
    @SerializedName("font_color") val fontColor: String,
    @SerializedName("bg_color") val bgColor: String
)

data class Media(
    val id: Int,
    val name: String,
    val type: String,
    @SerializedName("file_path") val filePath: String,
    @SerializedName("thumbnail_path") val thumbnailPath: String?,
    @SerializedName("duration_seconds") val durationSeconds: Int?,
    @SerializedName("file_size") val fileSize: Int,
    @SerializedName("ppt_images") val pptImages: List<String>?,
    @SerializedName("ppt_slide_duration") val pptSlideDuration: Int,
    @SerializedName("created_at") val createdAt: String
)

data class DisplayRegister(
    val name: String,
    @SerializedName("group_name") val groupName: String = "default",
    @SerializedName("screen_width") val screenWidth: Int,
    @SerializedName("screen_height") val screenHeight: Int,
    val platform: String = "android",
    @SerializedName("ip_address") val ipAddress: String? = null,
    @SerializedName("mac_address") val macAddress: String? = null
)

data class DisplayRegisterResponse(
    val id: Int,
    val name: String,
    @SerializedName("player_token") val playerToken: String?
)

data class HeartbeatData(
    @SerializedName("display_id") val displayId: Int,
    @SerializedName("player_version") val playerVersion: String,
    @SerializedName("screen_width") val screenWidth: Int,
    @SerializedName("screen_height") val screenHeight: Int,
    val platform: String = "android",
    @SerializedName("ip_address") val ipAddress: String? = null
)

data class CommandRequest(
    val command: String,
    @SerializedName("display_ids") val displayIds: List<Int>
)

data class CommandResult(
    val command: String,
    val success: Boolean,
    @SerializedName("error_message") val errorMessage: String? = null
)

enum class ConnectionState {
    CONNECTING,
    CONNECTED,
    ERROR,
    OFFLINE
}
