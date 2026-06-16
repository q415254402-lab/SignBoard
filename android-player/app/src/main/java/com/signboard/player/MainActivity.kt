package com.signboard.player

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.signboard.player.api.ApiClient
import com.signboard.player.model.DisplayRegister
import kotlinx.coroutines.*

class MainActivity : AppCompatActivity() {

    private lateinit var etServerUrl: EditText
    private lateinit var etDisplayName: EditText
    private lateinit var btnStart: Button

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val PERMISSION_REQUEST = 1001

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 先请求权限
        if (!checkPermissions()) {
            requestPermissions()
            return
        }

        // 从角落点击进入设置时，不自动跳转播放器
        val isSettingsMode = intent?.action == "OPEN_SETTINGS"

        // 检查是否已有配置，直接跳转播放器
        val prefs = getSharedPreferences("signboard", MODE_PRIVATE)
        val savedDisplayId = prefs.getInt("display_id", 0)
        val savedToken = prefs.getString("player_token", "")
        val savedUrl = prefs.getString("server_url", "")

        if (savedDisplayId > 0 && !savedToken.isNullOrEmpty() && !isSettingsMode) {
            // 必须先设置服务器地址，再跳转播放器
            val urlToUse = if (!savedUrl.isNullOrEmpty()) savedUrl else "http://192.168.1.100:8000"
            android.util.Log.d("MainActivity", "自动连接: displayId=$savedDisplayId, url=$urlToUse")
            ApiClient.updateBaseUrl(urlToUse)
            launchPlayer(savedDisplayId, savedToken)
            return
        }

        // 无配置，显示配置界面
        setContentView(R.layout.activity_main)

        etServerUrl = findViewById(R.id.etServerUrl)
        etDisplayName = findViewById(R.id.etDisplayName)
        btnStart = findViewById(R.id.btnStart)

        etServerUrl.setText(prefs.getString("server_url", "http://192.168.1.100:8000"))
        etDisplayName.setText(prefs.getString("display_name", "Android 屏幕"))

        btnStart.setOnClickListener { startPlayer() }
    }

    private fun checkPermissions(): Boolean {
        // 检查存储权限
        val storageOk = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_IMAGES) == PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED &&
                   ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        }
        
        // 检查 WRITE_SETTINGS 权限
        val settingsOk = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Settings.System.canWrite(this)
        } else {
            true
        }
        
        return storageOk && settingsOk
    }

    private fun requestPermissions() {
        // 请求存储权限
        val permissions = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.READ_MEDIA_IMAGES)
        } else {
            permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            permissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
        ActivityCompat.requestPermissions(this, permissions.toTypedArray(), PERMISSION_REQUEST)
        
        // 请求 WRITE_SETTINGS 权限（需要跳转系统设置）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.System.canWrite(this)) {
            Toast.makeText(this, "请在设置中允许修改系统设置", Toast.LENGTH_LONG).show()
            val intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST) {
            // 权限处理完成，继续
            val prefs = getSharedPreferences("signboard", MODE_PRIVATE)
            val savedDisplayId = prefs.getInt("display_id", 0)
            val savedToken = prefs.getString("player_token", "")
            val savedUrl = prefs.getString("server_url", "")
            
            if (savedDisplayId > 0 && !savedToken.isNullOrEmpty()) {
                // 必须先设置服务器地址
                if (!savedUrl.isNullOrEmpty()) {
                    ApiClient.updateBaseUrl(savedUrl)
                }
                launchPlayer(savedDisplayId, savedToken)
            } else {
                // 显示配置界面
                setContentView(R.layout.activity_main)
                etServerUrl = findViewById(R.id.etServerUrl)
                etDisplayName = findViewById(R.id.etDisplayName)
                btnStart = findViewById(R.id.btnStart)
                etServerUrl.setText(prefs.getString("server_url", "http://192.168.1.100:8000"))
                etDisplayName.setText(prefs.getString("display_name", "Android 屏幕"))
                btnStart.setOnClickListener { startPlayer() }
            }
        }
    }

    private fun launchPlayer(displayId: Int, token: String) {
        val intent = Intent(this, PlayerActivity::class.java).apply {
            putExtra("display_id", displayId)
            putExtra("player_token", token)
        }
        startActivity(intent)
        finish()
    }

    private fun startPlayer() {
        val serverUrl = etServerUrl.text.toString().trim()
        val displayName = etDisplayName.text.toString().trim()

        if (serverUrl.isEmpty()) {
            Toast.makeText(this, "请输入服务器地址", Toast.LENGTH_SHORT).show()
            return
        }
        if (displayName.isEmpty()) {
            Toast.makeText(this, "请输入屏幕名称", Toast.LENGTH_SHORT).show()
            return
        }

        val prefs = getSharedPreferences("signboard", MODE_PRIVATE)
        prefs.edit().putString("server_url", serverUrl).putString("display_name", displayName).apply()

        ApiClient.updateBaseUrl(serverUrl)

        scope.launch {
            try {
                btnStart.isEnabled = false
                btnStart.text = "连接中..."

                val dm = resources.displayMetrics
                val ip = getLocalIpAddress()
                val mac = getMacAddress()
                val response = ApiClient.apiService.register(
                    DisplayRegister(
                        name = displayName,
                        screenWidth = dm.widthPixels,
                        screenHeight = dm.heightPixels,
                        platform = "android",
                        ipAddress = ip,
                        macAddress = mac
                    )
                )

                if (response.isSuccessful) {
                    val data = response.body()!!
                    prefs.edit().putInt("display_id", data.id).putString("player_token", data.playerToken).apply()
                    launchPlayer(data.id, data.playerToken ?: "")
                } else {
                    Toast.makeText(this@MainActivity, "注册失败: ${response.code()}", Toast.LENGTH_LONG).show()
                    btnStart.isEnabled = true
                    btnStart.text = "启动播放"
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "连接失败: ${e.message}", Toast.LENGTH_LONG).show()
                btnStart.isEnabled = true
                btnStart.text = "启动播放"
            }
        }
    }

    private fun getLocalIpAddress(): String {
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                val addresses = networkInterface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val address = addresses.nextElement()
                    if (!address.isLoopbackAddress && address is java.net.Inet4Address) {
                        return address.hostAddress ?: ""
                    }
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("MainActivity", "获取 IP 地址失败", e)
        }
        return ""
    }

    private fun getMacAddress(): String {
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                if (networkInterface.isLoopback || !networkInterface.isUp) continue
                val mac = networkInterface.hardwareAddress
                if (mac != null) {
                    return mac.joinToString(":") { String.format("%02X", it) }
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("MainActivity", "获取 MAC 地址失败", e)
        }
        return ""
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }
}
