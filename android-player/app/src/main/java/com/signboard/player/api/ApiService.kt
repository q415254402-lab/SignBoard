package com.signboard.player.api

import com.signboard.player.model.*
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    
    @POST("api/v1/displays/register")
    suspend fun register(@Body data: DisplayRegister): Response<DisplayRegisterResponse>
    
    @GET("api/v1/player/sync/{displayId}")
    suspend fun sync(
        @Path("displayId") displayId: Int,
        @Header("X-Player-Token") token: String
    ): Response<SyncResponse>
    
    @GET("api/v1/player/download/{path}")
    suspend fun downloadMedia(
        @Path("path") path: String,
        @Header("X-Player-Token") token: String
    ): Response<ResponseBody>
    
    @POST("api/v1/displays/{displayId}/heartbeat")
    suspend fun heartbeat(
        @Path("displayId") displayId: Int,
        @Body data: HeartbeatData,
        @Header("X-Player-Token") token: String
    ): Response<Unit>
    
    @Multipart
    @POST("api/v1/displays/{displayId}/screenshot")
    suspend fun uploadScreenshot(
        @Path("displayId") displayId: Int,
        @Part file: okhttp3.MultipartBody.Part,
        @Header("X-Player-Token") token: String
    ): Response<Unit>
    
    @POST("api/v1/displays/command")
    suspend fun sendCommand(
        @Body data: CommandRequest
    ): Response<Unit>
}
