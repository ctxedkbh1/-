@echo off
chcp 65001 >nul
title 论文智能研究与写作助手 - 完整版
cd /d "%~dp0"

echo ==============================================
echo   论文智能研究与写作助手 - 完整版
echo ==============================================
echo.

echo [1/5] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python。请安装 Python 3.10 及以上版本，
    echo        安装时务必勾选 "Add python.exe to PATH"。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)
python --version

echo.
echo [1.5/5] 读取版本号...
for /f "delims=" %%v in ('python -c "from core import paths; print(paths.VERSION)"') do set APPVER=%%v
echo 当前版本: v%APPVER%
set "FULLNAME=论文智能研究与写作助手_完整版_v%APPVER%"
set "SINGLENAME=论文智能研究与写作助手_v%APPVER%"

echo.
echo [2/5] 安装依赖（优先使用清华镜像）...
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120
if errorlevel 1 python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [3/5] 运行自检...
python main.py --selfcheck
if errorlevel 1 (
    echo [错误] 自检未通过，请查看上方错误信息。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [4/5] PyInstaller 打包完整版目录（需要几分钟，请耐心等待）...
python -m PyInstaller --noconfirm --clean --onedir --windowed ^
    --collect-submodules keyring.backends ^
    --name "%FULLNAME%" main.py
if errorlevel 1 (
    echo [错误] 打包失败。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [4.5/5] PyInstaller 打包桌面单文件 EXE...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --collect-submodules keyring.backends ^
    --name "%SINGLENAME%" main.py
if errorlevel 1 (
    echo [错误] 单文件 EXE 打包失败。
    if not defined PAPERASSISTANT_NO_PAUSE pause
    exit /b 1
)

echo.
echo [5/5] 复制完整版文件夹和单文件 EXE 到桌面...
set "DESKTOP_FULL=%USERPROFILE%\Desktop\论文智能研究与写作助手_完整版"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "scripts\deploy_full_version.ps1" ^
    -SourceDir "dist\%FULLNAME%" -DestinationDir "%DESKTOP_FULL%" ^
    -DesktopDir "%USERPROFILE%\Desktop"
if errorlevel 1 (
    echo [警告] 复制到桌面失败，完整版位于 dist 目录。
) else (
    echo [完成] 完整版目录与旧配置已部署: %DESKTOP_FULL%
)
copy /Y "dist\%SINGLENAME%.exe" "%USERPROFILE%\Desktop\论文智能研究与写作助手.exe" >nul
if errorlevel 1 (
    echo [警告] 单文件 EXE 复制到桌面失败。
) else (
    echo [完成] 单文件 EXE 已更新: %USERPROFILE%\Desktop\论文智能研究与写作助手.exe
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "scripts\copy_release_asset.ps1" -Version "%APPVER%" -Kind exe
if errorlevel 1 (
    echo [错误] GitHub 单文件资产生成失败。
    exit /b 1
)

echo.
echo 桌面完整版文件夹已包含 EXE 和完整运行环境, 请保留整个文件夹.
REM Version: v2.3.0 (2026-08-19) Update: stable Windows PowerShell invocation
if not defined PAPERASSISTANT_NO_PAUSE pause
exit /b 0
