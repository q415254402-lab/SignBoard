"""统一日志配置"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(level=logging.INFO, log_to_file=True, log_dir="logs"):
    """配置全局日志
    
    Args:
        level: 日志级别
        log_to_file: 是否输出到文件
        log_dir: 日志目录
    """
    root = logging.getLogger()
    root.setLevel(level)
    
    # 避免重复添加 handler
    if root.handlers:
        return
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 控制台输出
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)
    
    # 文件输出
    if log_to_file:
        try:
            # 获取日志目录（打包后在 exe 同级目录）
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            log_path = os.path.join(base_dir, log_dir)
            os.makedirs(log_path, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                os.path.join(log_path, "signboard.log"),
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except Exception:
            pass  # 文件日志失败不影响控制台输出
