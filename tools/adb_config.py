"""
Android 播放器配置修改工具

用法：
  python adb_config.py                    # 交互模式
  python adb_config.py --url http://IP:8000 --name "设备名"  # 直接修改
  python adb_config.py --clear            # 清除配置重新注册
  python adb_config.py --list             # 列出已连接设备
"""

import subprocess
import sys
import argparse

PKG = "com.signboard.player"
RECEIVER = f"{PKG}/.ConfigReceiver"
ACTION_CHANGE = f"{PKG}.CONFIG_CHANGE"
ACTION_CLEAR = f"{PKG}.CONFIG_CLEAR"


def run_adb(args, device=None):
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += args
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip(), result.returncode


def list_devices():
    output, _ = run_adb(["devices"])
    devices = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def broadcast(device, action, extras=None):
    cmd = ["shell", "am", "broadcast", "-a", action]
    if extras:
        for k, v in extras.items():
            cmd += ["--es", k, v]
    cmd.append(RECEIVER)
    output, code = run_adb(cmd, device)
    return output, code


def force_stop(device):
    run_adb(["shell", "am", "force-stop", PKG], device)


def start_app(device):
    run_adb(["shell", "am", "start", "-n", f"{PKG}/.MainActivity"], device)


def select_device(devices):
    if len(devices) == 0:
        print("未检测到设备，请确认 USB 连接或 ADB 无线连接")
        sys.exit(1)
    if len(devices) == 1:
        print(f"检测到设备: {devices[0]}")
        return devices[0]
    print("检测到多个设备：")
    for i, d in enumerate(devices):
        print(f"  [{i + 1}] {d}")
    while True:
        choice = input(f"选择设备 (1-{len(devices)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(devices):
            return devices[int(choice) - 1]
        print("输入无效")


def main():
    parser = argparse.ArgumentParser(description="Android 播放器配置修改工具")
    parser.add_argument("--list", action="store_true", help="列出已连接设备")
    parser.add_argument("-s", "--device", help="指定设备序列号")
    parser.add_argument("--url", default="http://192.168.3.254:8000", help="服务器地址 (默认 http://192.168.3.254:8000)")
    parser.add_argument("--name", default="Android屏幕", help="设备名称 (默认 Android屏幕)")
    parser.add_argument("--clear", action="store_true", help="清除配置（重新注册）")
    parser.add_argument("--grant", action="store_true", help="授权系统设置权限（WRITE_SETTINGS）")
    parser.add_argument("--restart", action="store_true", help="修改后重启播放器")
    args = parser.parse_args()

    # 列出设备
    if args.list:
        devices = list_devices()
        if not devices:
            print("未检测到设备")
        else:
            print(f"已连接设备 ({len(devices)}):")
            for d in devices:
                print(f"  {d}")
        return

    # 获取设备
    devices = list_devices()
    device = args.device if args.device else select_device(devices)

    # 授权权限
    if args.grant:
        print(f"授权 {device} 系统设置权限...")
        run_adb(["shell", "appops", "set", PKG, "WRITE_SETTINGS", "allow"], device)
        run_adb(["shell", "appops", "set", PKG, "SYSTEM_ALERT_WINDOW", "allow"], device)
        print("  权限已授权（WRITE_SETTINGS + SYSTEM_ALERT_WINDOW）")
        return

    # 清除配置
    if args.clear:
        print(f"清除设备 {device} 的配置...")
        output, code = broadcast(device, ACTION_CLEAR)
        print(f"  {output}")
        if code == 0:
            force_stop(device)
            start_app(device)
            print("  已重启播放器，将进入设置页面")
        return

    # 修改配置
    if not args.url and not args.name:
        # 交互模式
        print(f"当前设备: {device}")
        print("（直接回车跳过不修改）")
        url = input("服务器地址: ").strip() or None
        name = input("设备名称: ").strip() or None
        if not url and not name:
            print("未输入任何配置，退出")
            return
    else:
        url = args.url
        name = args.name

    extras = {}
    if url:
        extras["server_url"] = url
    if name:
        extras["display_name"] = name

    print(f"修改设备 {device} 的配置:")
    if url:
        print(f"  服务器: {url}")
    if name:
        print(f"  名称: {name}")

    output, code = broadcast(device, ACTION_CHANGE, extras)
    print(f"  {output}")

    # 重启
    restart = args.restart
    if not restart and (url or name):
        choice = input("是否重启播放器? (y/N): ").strip().lower()
        restart = choice == "y"

    if restart:
        force_stop(device)
        start_app(device)
        print("  已重启播放器")


if __name__ == "__main__":
    main()
