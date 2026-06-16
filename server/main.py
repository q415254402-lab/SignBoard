"""SignBoard 服务端主入口

打包后:
    signboard-server.exe              # 默认端口 8000
    signboard-server.exe --port 9000  # 指定端口
    signboard-server.exe --no-gui     # 纯控制台模式（纯 Web API）
"""

import sys
import os
import argparse
import threading
import webbrowser
import logging
import secrets
import string

# ============================================================
# PyInstaller 打包时，runtime_hook.py 在 bootloader 阶段设置好了
# Qt6 的 DLL 搜索路径和插件路径。这里不需要重复设置。
# ============================================================

import socket

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_upload_dir, get_templates_dir, DEFAULT_CONFIG, BASE_DIR, RESOURCE_DIR
from shared.logging_config import setup_logging

from server.models import init_db, SessionLocal, DisplayModel
from server.api.media import router as media_router
from server.api.layout import router as layout_router
from server.api.schedule import router as schedule_router
from server.api.display import router as display_router
from server.api.player_sync import router as player_router
from server.api.auth import router as auth_router
from server.api.device_group import router as device_group_router
from server.api.audit import router as audit_router
from server.api.tag import router as tag_router
from server.api.power_schedule import router as power_schedule_router
from server.api.command_log import router as command_log_router

logger = logging.getLogger(__name__)


def get_local_ip():
    """获取本机局域网 IP（不依赖 Qt）"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.254.254.254", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# ---- FastAPI App ----

def create_app() -> FastAPI:
    global app
    app = FastAPI(
        title="SignBoard 数字标牌系统",
        version="2.2.1",
        docs_url="/api/docs",
    )

    # 心跳超时检测 + 过期 token 清理（后台定时任务）
    @app.on_event("startup")
    async def start_background_tasks():
        import asyncio
        timeout_minutes = DEFAULT_CONFIG.get("heartbeat_timeout_minutes", 2)

        # 启动时打印诊断信息
        templates_root = get_templates_dir()
        index_path = os.path.join(templates_root, "admin", "index.html")
        from shared.config import get_db_path
        logger.info(f"RESOURCE_DIR: {RESOURCE_DIR}")
        logger.info(f"BASE_DIR:     {BASE_DIR}")
        logger.info(f"模板目录:      {templates_root}")
        logger.info(f"index.html:   {'存在' if os.path.exists(index_path) else '不存在!'}")
        logger.info(f"数据库:        {get_db_path()}")

        def _do_background_task():
            """后台任务实际执行（同步，在线程池中运行）"""
            from datetime import datetime, timedelta
            db = SessionLocal()
            try:
                # 心跳超时检测
                timeout = datetime.now() - timedelta(minutes=timeout_minutes)
                stale = db.query(DisplayModel).filter(
                    DisplayModel.status == "online",
                    DisplayModel.last_heartbeat < timeout
                ).all()
                for d in stale:
                    d.status = "offline"
                if stale:
                    db.commit()
                # 清理过期 token
                from server.models import TokenModel
                expired = db.query(TokenModel).filter(
                    TokenModel.expires_at < datetime.now()
                ).delete()
                if expired:
                    db.commit()
                # 清理过期素材
                _cleanup_expired_media(db)
                # 清理 7 天前的截图
                _cleanup_old_screenshots(7)
                # 开关机计划调度
                _check_power_schedules(db)
            finally:
                db.close()

        async def background_loop():
            while True:
                try:
                    await asyncio.to_thread(_do_background_task)
                except Exception:
                    logger.exception("后台任务执行失败")
                await asyncio.sleep(60)
        asyncio.create_task(background_loop())

    # CORS — LAN 范围安全策略
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*", "http://127.0.0.1:*", "http://192.168.*.*", "http://10.*"],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Player-Token"],
    )

    # 注册路由
    api_prefix = DEFAULT_CONFIG["api_prefix"]
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(media_router, prefix=api_prefix)
    app.include_router(layout_router, prefix=api_prefix)
    app.include_router(schedule_router, prefix=api_prefix)
    app.include_router(display_router, prefix=api_prefix)
    app.include_router(player_router, prefix=api_prefix)
    app.include_router(device_group_router, prefix=api_prefix)
    app.include_router(audit_router, prefix=api_prefix)
    app.include_router(tag_router, prefix=api_prefix)
    app.include_router(power_schedule_router, prefix=api_prefix)
    app.include_router(command_log_router, prefix=api_prefix)

    # 鉴权中间件
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import RedirectResponse

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            path = request.url.path
            # 不需要鉴权的路径
            skip_paths = [
                "/api/v1/auth/login",
                "/api/v1/auth/logout",
                "/api/v1/displays/register",  # Player 首次注册无需 Token
                "/api/docs",
                "/openapi.json",
                "/assets/",
                "/login",
                "/favicon.ico",
                "/health",
            ]
            if any(path.startswith(p) for p in skip_paths):
                return await call_next(request)

            # 截图端点：Player 上传/获取截图（允许 Player token 或管理员 cookie）
            if "/screenshot" in path and "/displays/" in path:
                if _verify_player_token(request):
                    return await call_next(request)
                if _verify_admin_cookie(request):
                    return await call_next(request)
                from starlette.responses import JSONResponse
                return JSONResponse({"detail": "未授权"}, status_code=401)

            # Player API 端点：验证 player token
            player_paths = [
                "/api/v1/player/",
            ]
            # heartbeat 端点格式是 /displays/{id}/heartbeat，需要用 in 检查
            is_player_heartbeat = "/displays/" in path and "/heartbeat" in path
            
            if any(path.startswith(p) for p in player_paths) or is_player_heartbeat:
                if _verify_player_token(request):
                    return await call_next(request)
                from starlette.responses import JSONResponse
                return JSONResponse({"detail": "Player 认证失败"}, status_code=401)

            # 管理员 API：检查 cookie
            if _verify_admin_cookie(request):
                return await call_next(request)

            # 未登录
            if path.startswith("/api/"):
                from starlette.responses import JSONResponse
                return JSONResponse({"detail": "未登录"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)

    app.add_middleware(AuthMiddleware)

    # 静态文件 — 使用 RESOURCE_DIR 兼容 PyInstaller 打包
    templates_root = get_templates_dir()
    admin_dir = os.path.join(templates_root, "admin")

    # Vite build 产物的 assets 目录
    assets_dir = os.path.join(admin_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if os.path.isdir(templates_root):
        app.mount("/static", StaticFiles(directory=templates_root), name="static")

    # 上传目录静态服务
    upload_dir = get_upload_dir()
    if os.path.isdir(upload_dir):
        app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    # 健康检查（免鉴权）
    @app.get("/health")
    def health():
        result = {
            "status": "ok",
            "version": "2.0.0",
        }
        # 数据库检查
        try:
            db = SessionLocal()
            online_count = db.query(DisplayModel).filter(DisplayModel.status == "online").count()
            total_count = db.query(DisplayModel).count()
            db.close()
            result["database"] = "ok"
            result["displays"] = {"online": online_count, "total": total_count}
        except Exception as e:
            result["database"] = f"error: {str(e)}"
            result["status"] = "degraded"
        return result

    # SPA fallback: 非 API 路径返回 index.html（Vue Router hash 模式）
    from fastapi.responses import FileResponse, HTMLResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API 路径不处理
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path.startswith("assets/") or full_path.startswith("static/"):
            from starlette.responses import JSONResponse
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index_path = os.path.join(admin_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return HTMLResponse(
            f"<h1>模板文件未找到</h1>"
            f"<p>查找路径: {index_path}</p>"
            f"<p>RESOURCE_DIR: {RESOURCE_DIR}</p>"
            f"<p>BASE_DIR: {BASE_DIR}</p>"
            f"<p>请确认 server/templates/admin/index.html 文件存在。</p>",
            status_code=500,
        )

    return app


def _verify_player_token(request) -> bool:
    """验证 Player 端请求的 token"""
    import hmac
    from server.models import get_or_create_player_secret
    token = request.headers.get("X-Player-Token", "")
    if not token:
        return False
    expected = get_or_create_player_secret()
    return hmac.compare_digest(token, expected)


def _verify_admin_cookie(request) -> bool:
    """验证管理员 cookie"""
    from server.models import TokenModel
    from datetime import datetime
    token = request.cookies.get("signboard_token")
    if not token:
        return False
    db = SessionLocal()
    try:
        exists = db.query(TokenModel).filter(
            TokenModel.token == token,
            TokenModel.expires_at > datetime.now(),
        ).first()
        return exists is not None
    finally:
        db.close()


# ---- 在线数量查询 ----

def _cleanup_expired_media(db):
    """清理过期素材"""
    from datetime import datetime
    from server.models import MediaModel, media_tags
    from shared.config import get_upload_dir
    import shutil

    expired = db.query(MediaModel).filter(
        MediaModel.expires_at != None,
        MediaModel.expires_at < datetime.now()
    ).all()

    if not expired:
        return

    upload_dir = get_upload_dir()
    for m in expired:
        # 删除文件
        file_path = os.path.join(upload_dir, m.file_path)
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path, ignore_errors=True)
        if m.thumbnail_path:
            thumb_path = os.path.join(upload_dir, m.thumbnail_path)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        # 删除标签关联
        db.execute(media_tags.delete().where(media_tags.c.media_id == m.id))
        db.delete(m)

    db.commit()
    logger.info(f"已清理 {len(expired)} 个过期素材")


def _cleanup_old_screenshots(retention_days: int = 7):
    """清理超过 retention_days 天的截图文件"""
    import time
    from shared.config import get_upload_dir

    upload_dir = get_upload_dir()
    ss_dir = os.path.join(upload_dir, "screenshots")
    if not os.path.isdir(ss_dir):
        return

    cutoff = time.time() - retention_days * 86400
    for fname in os.listdir(ss_dir):
        if not fname.startswith("display_") or not fname.endswith(".jpg"):
            continue
        fpath = os.path.join(ss_dir, fname)
        try:
            if os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
        except OSError:
            pass


# 开关机计划当天已执行记录：{(plan_id, display_id, "on"): True, ...}
_power_executed_today: dict[str, bool] = {}


def _check_power_schedules(db):
    """检查开关机计划，下发 screen_on/screen_off 命令"""
    from server.models import PowerScheduleModel, DisplayModel
    from datetime import datetime

    now = datetime.now()
    current_time = now.strftime("%H:%M")
    weekday = str(now.today().weekday())  # 0=周一 ... 6=周日
    today_key = now.strftime("%Y-%m-%d")

    plans = db.query(PowerScheduleModel).filter(PowerScheduleModel.is_enabled == True).all()

    for plan in plans:
        power_days = plan.power_days or "1,2,3,4,5"
        # power_days 用的是周几数字（0=周日,1=周一...6=周六），Python weekday 是 0=周一
        # 需要转换：数据库的 0=周日，weekday 的 6=周日
        day_map = {"0": "6", "1": "0", "2": "1", "3": "2", "4": "3", "5": "4", "6": "5"}
        plan_days = set(day_map.get(d.strip(), d.strip()) for d in power_days.split(",") if d.strip())

        if weekday not in plan_days:
            continue

        display_ids = plan.get_display_ids()
        if not display_ids:
            # 未绑定设备 = 全部在线设备
            displays = db.query(DisplayModel).filter(DisplayModel.status == "online").all()
            display_ids = [d.id for d in displays]

        for did in display_ids:
            d = db.query(DisplayModel).filter(DisplayModel.id == did).first()
            if not d or d.status != "online":
                continue

            # 开机
            if plan.on_time and current_time == plan.on_time:
                exec_key = f"{today_key}_{plan.id}_{did}_on"
                if exec_key not in _power_executed_today:
                    _power_executed_today[exec_key] = True
                    d.add_command("screen_on")
                    db.commit()
                    from server.api.command_log import log_command
                    log_command(db, display_id=did, display_name=d.name,
                                command="screen_on", triggered_by="schedule")
                    logger.info(f"开关机计划: {plan.name} -> {d.name} 开机")

            # 关机
            if plan.off_time and current_time == plan.off_time:
                exec_key = f"{today_key}_{plan.id}_{did}_off"
                if exec_key not in _power_executed_today:
                    _power_executed_today[exec_key] = True
                    d.add_command("screen_off")
                    db.commit()
                    from server.api.command_log import log_command
                    log_command(db, display_id=did, display_name=d.name,
                                command="screen_off", triggered_by="schedule")
                    logger.info(f"开关机计划: {plan.name} -> {d.name} 关机")

    # 清理非今天的记录
    stale_keys = [k for k in _power_executed_today if not k.startswith(today_key)]
    for k in stale_keys:
        del _power_executed_today[k]


def get_online_count() -> int:
    """获取在线屏幕数量"""
    try:
        db = SessionLocal()
        count = db.query(DisplayModel).filter(DisplayModel.status == "online").count()
        db.close()
        return count
    except Exception:
        return 0


# ---- 启动入口 ----

def main():
    parser = argparse.ArgumentParser(
        description="SignBoard 服务端",
        epilog="示例: signboard-server.exe --port 9000 --no-gui",
    )
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--no-gui", action="store_true", help="不显示状态窗口（纯控制台模式）")
    parser.add_argument("--reset-password", type=str, metavar="USERNAME", help="重置指定用户的密码")
    try:
        args = parser.parse_args()
    except SystemExit:
        print("\n错误: 参数格式不正确。请使用双横杠，例如: --no-gui、--port 9000")
        print("用法: signboard-server.exe [--port 端口] [--no-gui] [--no-browser]\n")
        sys.exit(1)

    # 初始化日志
    setup_logging(level="INFO")

    # 处理重置密码
    if args.reset_password:
        init_db()
        from server.models import SessionLocal, UserModel, hash_password
        db = SessionLocal()
        user = db.query(UserModel).filter(UserModel.username == args.reset_password).first()
        if not user:
            print(f"用户 '{args.reset_password}' 不存在")
            db.close()
            sys.exit(1)
        # 生成随机密码，不再依赖硬编码
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_pw = ''.join(secrets.choice(alphabet) for _ in range(16))
        user.password_hash = hash_password(new_pw)
        db.commit()
        db.close()
        print(f"用户 '{args.reset_password}' 的密码已重置为: {new_pw}")
        print("请登录后立即修改密码。")
        sys.exit(0)

    # 初始化数据库
    init_db()

    # 启动状态窗口
    if not args.no_gui:
        try:
            from PyQt6.QtWidgets import QApplication
            from server.status_window import StatusWindow

            qt_app = QApplication(sys.argv)
            window = StatusWindow(args.port, get_online_count)
            window.show()

            # 自动打开浏览器
            if not args.no_browser:
                webbrowser.open(f"http://{get_local_ip()}:{args.port}")

            # FastAPI 在后台线程启动
            app = create_app()

            def run_server():
                uvicorn.run(app, host=args.host, port=args.port, log_level="info")

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            sys.exit(qt_app.exec())
        except ImportError as e:
            print(f"[WARN] GUI 模式启动失败（缺少 Qt 组件），自动降级为控制台模式: {e}")
            print("[WARN] 如需 GUI 状态窗口，请参考 Windows Server 安装桌面体验")
            # 降级为 no_gui 模式
            args.no_gui = True

    if args.no_gui:
        # 纯控制台模式
        app = create_app()
        if not args.no_browser:
            webbrowser.open(f"http://{get_local_ip()}:{args.port}")
        print(f"\n  SignBoard CMS 服务已启动")
        print(f"  管理页面: http://{get_local_ip()}:{args.port}")
        print(f"  API 文档: http://{get_local_ip()}:{args.port}/api/docs")
        print(f"  按 Ctrl+C 停止服务\n")
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
else:
    # uvicorn server.main:app 直接导入时创建 app
    app = create_app()
