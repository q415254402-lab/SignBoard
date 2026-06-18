"""PyInstaller 打包脚本 — Android APK

生成:
    android-player/app/build/outputs/apk/debug/app-debug.apk

用法:
    python build_android.py           # 默认 debug 版本
    python build_android.py release   # release 版本
"""

import os
import sys
import subprocess

root = os.path.dirname(os.path.abspath(__file__))
android_dir = os.path.join(root, "android-player")

# 检查 Android SDK
android_sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
if not android_sdk:
    default_sdk = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Android", "Sdk")
    if os.path.isdir(default_sdk):
        android_sdk = default_sdk
    else:
        print("[FAIL] 未找到 Android SDK，请设置 ANDROID_HOME 环境变量")
        sys.exit(1)

print(f"Android SDK: {android_sdk}")

# 检查 Java
java_home = os.environ.get("JAVA_HOME")
if not java_home:
    # 尝试常见路径
    possible_paths = [
        r"C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot",
        r"C:\Program Files\Eclipse Adoptium\jdk-17",
        r"C:\Program Files\Java\jdk-17",
    ]
    for p in possible_paths:
        if os.path.isdir(p):
            java_home = p
            break

if java_home:
    os.environ["JAVA_HOME"] = java_home
    print(f"JAVA_HOME: {java_home}")

os.environ["ANDROID_HOME"] = android_sdk
os.environ["ANDROID_SDK_ROOT"] = android_sdk

# 确定构建类型
build_type = sys.argv[1] if len(sys.argv) > 1 else "debug"
task = "assembleDebug" if build_type == "debug" else "assembleRelease"

print(f"\n构建类型: {build_type}")
print(f"任务: {task}")
print()

# 执行构建
gradlew = os.path.join(android_dir, "gradlew.bat")
if not os.path.exists(gradlew):
    print("[FAIL] 未找到 gradlew.bat")
    sys.exit(1)

result = subprocess.run(
    [gradlew, task, "--no-daemon"],
    cwd=android_dir,
    capture_output=False,
)

if result.returncode != 0:
    print(f"\n[FAIL] 构建失败，返回码: {result.returncode}")
    sys.exit(result.returncode)

# 查找输出的 APK
apk_dir = os.path.join(android_dir, "app", "build", "outputs", "apk", build_type)
if not os.path.isdir(apk_dir):
    print(f"[FAIL] 未找到 APK 输出目录: {apk_dir}")
    sys.exit(1)

apk_files = [f for f in os.listdir(apk_dir) if f.endswith(".apk")]
if not apk_files:
    print(f"[FAIL] 未找到 APK 文件")
    sys.exit(1)

apk_file = os.path.join(apk_dir, apk_files[0])
apk_size = os.path.getsize(apk_file) / 1024 / 1024

print()
print("=" * 50)
print("构建成功")
print("=" * 50)
print(f"  APK: {apk_file}")
print(f"  大小: {apk_size:.2f} MB")
print()
print("将 APK 传输到 Android 设备安装即可。")
