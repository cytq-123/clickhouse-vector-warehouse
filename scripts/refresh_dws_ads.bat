@echo off
REM Windows 环境下执行 DWS/ADS 层刷新
REM 需要先确保 Python 环境和依赖已安装

cd /d "%~dp0"

echo ==================================================
echo 数据仓库 DWS/ADS 层刷新
echo ==================================================
echo.

echo 步骤 1/2: 刷新 DWS 层汇总表...
python refresh_dws_layer.py
if %ERRORLEVEL% neq 0 (
    echo DWS 层刷新失败
    exit /b 1
)
echo.

echo 步骤 2/2: 刷新 ADS 层应用表...
python refresh_ads_layer.py
if %ERRORLEVEL% neq 0 (
    echo ADS 层刷新失败
    exit /b 1
)
echo.

echo ==================================================
echo √ DWS/ADS 层刷新完成！
echo ==================================================
echo.
echo 验证命令:
echo   docker exec clickhouse clickhouse-client --query="SELECT count() FROM dws_layer.user_order_summary"
echo   docker exec clickhouse clickhouse-client --query="SELECT count() FROM ads_layer.user_portrait"
echo.