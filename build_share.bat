@echo off
chcp 65001 >nul
title 论文智能研究与写作助手 - 分享版打包
cd /d "%~dp0"

echo ==============================================
echo   论文智能研究与写作助手 - 分享版打包工具
echo   Portable package - bundled Python runtime
echo ==============================================
echo.

echo [1/5] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python。请安装 Python 3.10 及以上版本，
    echo        安装时勾选 "Add python.exe to PATH"。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [1.5/5] 读取版本号...
for /f "delims=" %%v in ('python -c "from core import paths; print(paths.VERSION)"') do set APPVER=%%v
echo 当前版本: v%APPVER%

echo.
echo [2/5] 安装依赖...
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120
if errorlevel 1 python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [3/5] 运行自检...
python main.py --selfcheck
if errorlevel 1 (
    echo [错误] 自检未通过。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [4/5] PyInstaller 打包（目录模式，自带完整运行环境）...
python -m PyInstaller --noconfirm --clean --onedir --windowed ^
    --name "论文智能研究与写作助手_v%APPVER%" main.py
if errorlevel 1 (
    echo [错误] 打包失败。
    pause
    exit /b 1
)

echo.
echo [5/5] 压缩为分享包并复制到桌面...
if exist "论文助手_v%APPVER%.zip" del /Q "论文助手_v%APPVER%.zip"
tar -a -c -f "论文助手_v%APPVER%.zip" -C dist "论文智能研究与写作助手_v%APPVER%"
if errorlevel 1 (
    echo [警告] tar 压缩失败，改用 PowerShell 压缩...
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\论文智能研究与写作助手_v%APPVER%' -DestinationPath '论文助手_v%APPVER%.zip' -Force"
)
del /Q "%USERPROFILE%\Desktop\论文助手.zip" >nul 2>&1
copy /Y "论文助手_v%APPVER%.zip" "%USERPROFILE%\Desktop\论文助手.zip" >nul
if errorlevel 1 (
    echo [警告] 复制到桌面失败，ZIP 位于项目目录。
) else (
    echo [完成] 分享包: %USERPROFILE%\Desktop\论文助手.zip
)

echo.
echo 使用方法（接收方无需安装任何环境）:
echo   1. 把 ZIP 发给对方
echo   2. 对方解压后，双击文件夹内的 exe 即可
echo   3. 论文数据自动保存在 exe 同目录的 paper_project 文件夹中
echo 注意: 请整包发送，不要只发文件夹里的 exe。
REM Version: v2.0.1 (2026-08-17) Fix: enforce CRLF for cmd.exe
if not defined PAPERASSISTANT_NO_PAUSE pause
exit /b 0
