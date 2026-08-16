@echo off
chcp 65001 >nul
title 论文智能研究与写作助手 - 一键打包
cd /d "%~dp0"

echo ==============================================
echo   论文智能研究与写作助手 - 一键打包工具
echo ==============================================
echo.

echo [1/5] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python。请安装 Python 3.10 及以上版本，
    echo        安装时务必勾选 "Add python.exe to PATH"。
    pause
    exit /b 1
)
python --version

echo.
echo [1.5/5] 读取版本号...
for /f "delims=" %%v in ('python -c "from core import paths; print(paths.VERSION)"') do set APPVER=%%v
echo 当前版本: v%APPVER%

echo.
echo [2/5] 安装依赖（优先使用清华镜像）...
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120
if errorlevel 1 python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
)

echo.
echo [3/5] 运行自检...
python main.py --selfcheck
if errorlevel 1 (
    echo [错误] 自检未通过，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo [4/5] PyInstaller 打包（需要几分钟，请耐心等待）...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "论文智能研究与写作助手_v%APPVER%" main.py
if errorlevel 1 (
    echo [错误] 打包失败。
    pause
    exit /b 1
)

echo.
echo [5/5] 复制 EXE 到桌面...
del /Q "%USERPROFILE%\Desktop\论文智能研究与写作助手.exe" >nul 2>&1
copy /Y "dist\论文智能研究与写作助手_v%APPVER%.exe" "%USERPROFILE%\Desktop\论文智能研究与写作助手_v%APPVER%.exe" >nul
if errorlevel 1 (
    echo [警告] 复制到桌面失败，EXE 位于 dist 目录。
) else (
    echo [完成] 已生成: %USERPROFILE%\Desktop\论文智能研究与写作助手_v%APPVER%.exe
)

echo.
echo 双击桌面上的 EXE 即可使用，无需安装 Python 或其他环境。
echo 项目数据将自动保存在 EXE 同目录的 paper_project 文件夹中。
pause
