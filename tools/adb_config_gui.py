"""
Android 播放器配置修改工具 (GUI)

双击运行即可，需要安装 ADB。
支持 USB 和无线 ADB 连接。
"""

import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

PKG = "com.signboard.player"
RECEIVER = f"{PKG}/.ConfigReceiver"
ACTION_CHANGE = f"{PKG}.CONFIG_CHANGE"
ACTION_CLEAR = f"{PKG}.CONFIG_CLEAR"


def run_adb(args, device=None):
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "命令超时", -1
    except FileNotFoundError:
        return "未找到 adb，请确认已安装并加入 PATH", -1


def list_devices():
    output, _ = run_adb(["devices"])
    devices = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def connect_device(addr):
    output, code = run_adb(["connect", addr])
    return output, code


def disconnect_device(addr):
    output, code = run_adb(["disconnect", addr])
    return output, code


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Android 播放器配置工具")
        self.root.geometry("520x500")
        self.root.resizable(False, False)

        self._build_ui()
        self.refresh_devices()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ADB 连接
        frame_conn = ttk.LabelFrame(self.root, text="ADB 连接", padding=8)
        frame_conn.pack(fill="x", **pad)

        row1 = ttk.Frame(frame_conn)
        row1.pack(fill="x", pady=(0, 4))
        ttk.Label(row1, text="无线连接:").pack(side="left")
        self.conn_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.conn_var, width=25).pack(side="left", padx=(4, 0))
        ttk.Label(row1, text="(IP:端口)").pack(side="left", padx=(4, 0))
        self.btn_connect = ttk.Button(row1, text="连接", command=self.connect_adb, width=6)
        self.btn_connect.pack(side="right")

        row2 = ttk.Frame(frame_conn)
        row2.pack(fill="x")
        ttk.Label(row2, text="已连接设备:").pack(side="left")
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(row2, textvariable=self.device_var, state="readonly", width=28)
        self.device_combo.pack(side="left", padx=(4, 0), fill="x", expand=True)
        self.btn_refresh = ttk.Button(row2, text="刷新", command=self.refresh_devices, width=6)
        self.btn_refresh.pack(side="right", padx=(8, 0))
        self.btn_disconnect = ttk.Button(row2, text="断开", command=self.disconnect_adb, width=6)
        self.btn_disconnect.pack(side="right", padx=(4, 0))

        # 配置
        frame_config = ttk.LabelFrame(self.root, text="播放器配置", padding=8)
        frame_config.pack(fill="x", **pad)

        ttk.Label(frame_config, text="服务器地址:").grid(row=0, column=0, sticky="w", pady=4)
        self.url_var = tk.StringVar(value="http://192.168.3.254:8000")
        ttk.Entry(frame_config, textvariable=self.url_var, width=45).grid(row=0, column=1, pady=4)

        ttk.Label(frame_config, text="设备名称:").grid(row=1, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar(value="Android屏幕")
        ttk.Entry(frame_config, textvariable=self.name_var, width=45).grid(row=1, column=1, pady=4)

        self.auto_start_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_config, text="应用后自动启动播放器（无屏设备勾选）", variable=self.auto_start_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        # 按钮
        frame_btn = ttk.Frame(self.root, padding=8)
        frame_btn.pack(fill="x")

        self.btn_apply = ttk.Button(frame_btn, text="应用配置", command=self.apply_config)
        self.btn_apply.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_restart = ttk.Button(frame_btn, text="重启播放器", command=self.restart_app)
        self.btn_restart.pack(side="left", expand=True, fill="x", padx=(4, 0))

        frame_btn2 = ttk.Frame(self.root, padding=8)
        frame_btn2.pack(fill="x")

        self.btn_clear = ttk.Button(frame_btn2, text="清除配置（重新注册）", command=self.clear_config)
        self.btn_clear.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_grant = ttk.Button(frame_btn2, text="授权系统设置权限", command=self.grant_permissions)
        self.btn_grant.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # 日志
        frame_log = ttk.LabelFrame(self.root, text="日志", padding=8)
        frame_log.pack(fill="both", expand=True, **pad)

        self.log_text = tk.Text(frame_log, height=8, state="disabled", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(frame_log, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def get_device(self):
        device = self.device_var.get()
        if not device:
            messagebox.showwarning("提示", "请先选择设备")
            return None
        return device

    def refresh_devices(self):
        devices = list_devices()
        self.device_combo["values"] = devices
        if devices:
            self.device_combo.current(0)
            self.log(f"检测到 {len(devices)} 台设备")
        else:
            self.log("未检测到设备")

    def connect_adb(self):
        addr = self.conn_var.get().strip()
        if not addr:
            messagebox.showwarning("提示", "请输入设备 IP 地址和端口\n格式: 192.168.1.100:5555")
            return

        # 补充默认端口
        if ":" not in addr:
            addr += ":5555"
            self.conn_var.set(addr)

        self.log(f"连接 {addr}...")
        self.btn_connect.configure(state="disabled")

        def task():
            output, code = run_adb(["connect", addr])
            self.root.after(0, lambda: self._on_connect_result(addr, output, code))

        threading.Thread(target=task, daemon=True).start()

    def _on_connect_result(self, addr, output, code):
        self.btn_connect.configure(state="normal")
        self.log(f"  {output}")
        if "connected" in output.lower():
            self.refresh_devices()
            # 自动选中刚连接的设备
            values = self.device_combo["values"]
            if addr in values:
                self.device_var.set(addr)
        else:
            messagebox.showerror("连接失败", f"无法连接到 {addr}\n\n{output}\n\n请确认:\n1. 设备已开启无线调试\n2. IP 和端口正确\n3. 设备在同一局域网")

    def disconnect_adb(self):
        device = self.device_var.get()
        if not device:
            return
        self.log(f"断开 {device}...")
        output, code = run_adb(["disconnect", device], device)
        self.log(f"  {output}")
        self.refresh_devices()

    def apply_config(self):
        device = self.get_device()
        url = self.url_var.get().strip()
        name = self.name_var.get().strip()
        if not url and not name:
            messagebox.showwarning("提示", "请至少填写一项配置")
            return

        extras = []
        if url:
            extras += ["--es", "server_url", url]
        if name:
            extras += ["--es", "display_name", name]
        if self.auto_start_var.get():
            extras += ["--ez", "auto_start", "true"]

        self.log(f"发送配置到 {device}...")
        if url:
            self.log(f"  服务器: {url}")
        if name:
            self.log(f"  名称: {name}")

        def task():
            output, code = run_adb(["shell", "am", "broadcast", "-a", ACTION_CHANGE] + extras + [RECEIVER], device)
            self.root.after(0, lambda: self._on_broadcast_result(output, code))

        threading.Thread(target=task, daemon=True).start()

    def _on_broadcast_result(self, output, code):
        if "result=-1" in output or "not found" in output.lower():
            self.log(f"  失败: {output}")
            messagebox.showerror("失败", f"广播发送失败\n{output}\n\n请确认已安装新版本 APK")
            return

        self.log(f"  {output}")

        if self.auto_start_var.get():
            self.log("配置已发送，播放器已自动启动")
        else:
            self.log("配置已更新，重启播放器生效")
            if messagebox.askyesno("成功", "配置已发送成功\n是否立即重启播放器？"):
                self.restart_app()

    def restart_app(self):
        device = self.get_device()
        if not device:
            return
        self.log(f"重启 {device} 上的播放器...")
        run_adb(["shell", "am", "force-stop", PKG], device)
        run_adb(["shell", "am", "start", "-n", f"{PKG}/.MainActivity"], device)
        self.log("  已重启")

    def grant_permissions(self):
        device = self.get_device()
        if not device:
            return
        self.log(f"授权 {device} 系统设置权限...")
        perms = [
            ["shell", "appops", "set", PKG, "WRITE_SETTINGS", "allow"],
            ["shell", "appops", "set", PKG, "SYSTEM_ALERT_WINDOW", "allow"],
        ]
        for args in perms:
            output, code = run_adb(args, device)
            self.log(f"  {' '.join(args[-3:])}: {output or 'OK'}")
        self.log("  权限已授权（WRITE_SETTINGS + SYSTEM_ALERT_WINDOW）")

    def clear_config(self):
        device = self.get_device()
        if not device:
            return
        if not messagebox.askyesno("确认", "清除配置后需要重新注册\n确定继续？"):
            return
        self.log(f"清除 {device} 的配置...")
        output, code = run_adb(["shell", "am", "broadcast", "-a", ACTION_CLEAR, RECEIVER], device)
        self.log(f"  {output}")
        self.restart_app()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
