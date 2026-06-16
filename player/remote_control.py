"""远程控制模块 — 熄屏/唤醒/重启"""

import sys
import subprocess
import logging

logger = logging.getLogger(__name__)


class RemoteControl:
    """远程控制（Windows）"""

    def __init__(self):
        self._is_screen_off = False
        self._user32 = None
        if sys.platform == 'win32':
            try:
                import ctypes
                self._user32 = ctypes.windll.user32
            except Exception:
                pass

    def screen_off(self) -> bool:
        """立即熄屏"""
        if self._is_screen_off:
            return True

        # 方案 1：SendMessage SC_MONITORPOWER（立即熄屏）
        if self._user32:
            try:
                import ctypes
                # SC_MONITORPOWER = 0xF170, Monitor power off = 2
                # HWND_BROADCAST = 0xFFFF
                self._user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
                self._is_screen_off = True
                logger.info("屏幕已熄灭（SC_MONITORPOWER）")
                return True
            except Exception as e:
                logger.debug(f"SC_MONITORPOWER 失败: {e}")

        # 方案 2：SetMonitorPowerState（dxva2.dll）
        if sys.platform == 'win32':
            try:
                import ctypes
                dxva2 = ctypes.windll.dxva2
                user32 = ctypes.windll.user32
                # MONITOR_DEFAULTTONEAREST = 2
                monitor = user32.MonitorFromWindow(user32.GetDesktopWindow(), 2)
                if monitor:
                    dxva2.SetMonitorPowerState(monitor, False)
                    self._is_screen_off = True
                    logger.info("屏幕已熄灭（SetMonitorPowerState）")
                    return True
            except Exception as e:
                logger.debug(f"SetMonitorPowerState 失败: {e}")

        # 方案 3：降级到 powercfg
        try:
            subprocess.run(
                ["powercfg", "/change", "monitor-timeout-ac", "1"],
                capture_output=True, timeout=5
            )
            self._is_screen_off = True
            logger.info("屏幕已熄灭（powercfg 降级）")
            return True
        except Exception as e:
            logger.error(f"熄屏失败: {e}")
            return False

    def screen_on(self) -> bool:
        """立即唤醒"""
        if not self._is_screen_off:
            return True

        # 方案 1：模拟鼠标移动 + 按键唤醒
        if self._user32:
            try:
                # 模拟鼠标移动（唤醒屏幕）
                self._user32.mouse_event(0x0001, 0, 0, 0, 0)  # MOUSEEVENTF_MOVE
                # 模拟按键释放（VK_SPACE）
                self._user32.keybd_event(0x20, 0, 0x0002, 0)  # KEYEVENTF_KEYUP
                self._is_screen_off = False
                logger.info("屏幕已唤醒（mouse_event + keybd_event）")
                return True
            except Exception as e:
                logger.debug(f"唤醒失败: {e}")

        # 方案 2：降级到 powercfg 恢复超时为"从不"
        try:
            subprocess.run(
                ["powercfg", "/change", "monitor-timeout-ac", "0"],
                capture_output=True, timeout=5
            )
            self._is_screen_off = False
            logger.info("屏幕已唤醒（powercfg 降级，超时设为从不）")
            return True
        except Exception as e:
            logger.error(f"唤醒失败: {e}")
            return False

    def restart(self) -> bool:
        """重启系统"""
        try:
            subprocess.Popen(
                ["shutdown", "/r", "/t", "10", "/c", "SignBoard: 远程重启"]
            )
            logger.warning("收到远程重启指令，系统将在 10 秒后重启")
            return True
        except Exception as e:
            logger.error(f"重启失败: {e}")
            return False
