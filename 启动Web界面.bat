@echo off
chcp 65001 >nul
title A3 v3 个性化学习多智能体系统

echo ============================================================
echo   A3 v3 个性化学习多智能体系统
echo   六智能体 · DeepSeek 主力 · 讯飞星火交叉验证
echo ============================================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b
)

:: ============================================================================
:: 首次运行自动配置 API Key
:: ============================================================================
if not exist .env (
    echo.
    echo ============================================================
    echo   首次运行 —— 只需一步：粘贴 API Key
    echo ============================================================
    echo.
    echo 推荐注册 DeepSeek（注册送额度，10 块钱用很久）：
    echo   https://platform.deepseek.com
    echo 注册后点左侧「API Keys」→「创建新 Key」→ 复制 sk- 开头的那串
    echo.
    echo 没有 Key 的话直接按回车，系统会用内置星火兜底也能跑
    echo.

    :: 先复制模板
    copy .env.example .env >nul

    :: 用 PowerShell 做交互和替换（比批处理更稳，不丢特殊字符）
    powershell -ExecutionPolicy Bypass -Command "$key = Read-Host '请粘贴你的 DeepSeek API Key'; if ($key -and $key.Trim() -ne '') { $content = Get-Content .env -Encoding UTF8; $content = $content -replace 'DEEPSEEK_API_KEY=你的Key填这里', ('DEEPSEEK_API_KEY=' + $key.Trim()); $content | Set-Content .env -Encoding UTF8; Write-Host ''; Write-Host '√ API Key 已配置！' -ForegroundColor Green } else { Write-Host ''; Write-Host '√ 已跳过，系统使用内置星火兜底' -ForegroundColor Yellow }"
    echo.
)

:: ============================================================================
:: 检查依赖
:: ============================================================================
echo [1/2] 检查依赖...
pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖，请稍候...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
    echo 依赖安装完成！
) else (
    echo 依赖已就绪！
)

:: ============================================================================
:: 启动
:: ============================================================================
echo.
echo [2/2] 启动 Web 界面...
echo 服务就绪后浏览器将自动打开: http://localhost:8501
echo.
echo 按 Ctrl+C 可关闭服务
echo ============================================================
echo.

streamlit run app.py

pause
