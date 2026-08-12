@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 第五人格摸金娱乐赛 - 启动器

echo ================================================
echo    第五人格摸金娱乐赛 · 一键启动
echo    本机访问  http://127.0.0.1:8000
echo    局域网访问  http://本机IP:8000
echo ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python。
    echo        请先安装 Python 3.9+（安装时勾选 Add Python to PATH）。
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
python -m pip install -r backend\requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo [提示] 依赖安装未完成，继续尝试启动...
)
echo.

if not exist backend\.env (
    echo [2/3] 未检测到视觉AI配置（backend\.env）
    echo        将使用本地 OCR 识别引擎，功能完整可用。
    echo        如需视觉AI识图，按 README.md 配置后重启即可。
) else (
    echo [2/3] 已检测到视觉AI配置（backend\.env）
)
echo.

echo [3/3] 启动服务中... 请稍候
start "" http://127.0.0.1:8000
cd backend
python run.py

echo.
echo 服务已停止。按任意键退出...
pause >nul
