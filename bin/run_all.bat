@echo off
pushd "%~dp0"
setlocal enabledelayedexpansion

REM Python 実行コマンドの判定（MS Store のダミー python 対策。実際に動くコマンドを採用）
REM まず py ランチャーを試し、ダメなら python。どちらも -c で実行確認する。
set "PYTHON="
py -c "import sys" >nul 2>&1 && set "PYTHON=py"
if not defined PYTHON python -c "import sys" >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (
    echo [エラー] 動作する Python が見つかりません。Python をインストールするか py ランチャーを有効にしてください。
    pause
    exit /b
)

echo ======================================================
echo   按分計算・集計プロセス自動実行
echo ======================================================
echo.

REM 1. 年月の入力
echo 対象の年月を入力してください (例: 202603):
set /p TARGET_MONTH=

if "%TARGET_MONTH%"=="" (
    echo [エラー] 年月が入力されていません。終了します。
    pause
    exit /b
)

REM 2. envファイルからパスを取得
set "count=0"
if not exist "env" (
    echo [エラー] 環境設定ファイル 'env' が見つかりません。
    pause
    exit /b
)

for /f "usebackq tokens=*" %%a in ("env") do (
    set /a count+=1
    if !count! == 1 set "ROOT_DIR=%%a"
    if !count! == 3 set "MEMBER_SUB=%%a"
    if !count! == 4 set "KINTAI_SUB=%%a"
    if !count! == 7 set "RESULTS_SUB=%%a"
)

REM env 1行目が実在しなければパッケージルート(このbatの親)を使う（別PC/別ドライブ対応・Python側と整合）
if not exist "!ROOT_DIR!\" set "ROOT_DIR=%~dp0.."

REM 先頭の \ を除去してパスを結合
set "MEMBER_DIR=!ROOT_DIR!\!MEMBER_SUB:\=!"
set "KINTAI_DIR=!ROOT_DIR!\!KINTAI_SUB:\=!"
set "RESULTS_DIR=!ROOT_DIR!\!RESULTS_SUB:\=!"
set "SONEKI_DIR=!ROOT_DIR!\soneki"

echo.
echo --- ファイルの存在確認中 ---

REM (A) YYYYMM_raw_data.csv の確認
if not exist "!RESULTS_DIR!\%TARGET_MONTH%_raw_data.csv" (
    echo [×] 未検出: !RESULTS_DIR!\%TARGET_MONTH%_raw_data.csv
    goto :MISSING_ERROR
)
echo [OK] 検出: %TARGET_MONTH%_raw_data.csv

REM (B) 勤怠Excel(xls) の確認
dir /b "!KINTAI_DIR!\*%TARGET_MONTH%*kintai*.xls" >nul 2>&1
if errorlevel 1 (
    echo [×] 未検出: !KINTAI_DIR! 内の勤怠データ
    goto :MISSING_ERROR
)
echo [OK] 検出: 勤怠データ

REM (C) 損益Excel(xlsx) の確認 (年月指定なし)
set "SONEKI_FILE="
for /f "delims=" %%F in ('dir /b "!SONEKI_DIR!\*.xlsx" 2^>nul') do (
    if "!SONEKI_FILE!"=="" set "SONEKI_FILE=%%F"
)

if "!SONEKI_FILE!"=="" (
    echo [×] 未検出: !SONEKI_DIR! 内の損益データ
    goto :MISSING_ERROR
)
echo [OK] 検出: 損益データ 【!SONEKI_FILE!】

echo ------------------------------------------------------
echo 全てのファイルが揃いました。
echo.
echo ======================================================
echo 検出された損益データ: !SONEKI_FILE!
echo ======================================================
echo.

echo この損益データを使用して集計処理(2つのスクリプト)を開始しますか？
choice /C YN /M "Yes(Y) / No(N)"

if errorlevel 2 (
    echo.
    echo [中止] ユーザにより処理がキャンセルされました。
    pause
    exit /b
)

echo.
echo ------------------------------------------------------
echo [STEP 1] 実働時間按分 (allocate_actual_hours.py) 実行中...
echo ------------------------------------------------------
%PYTHON% allocate_actual_hours.py --month %TARGET_MONTH% --data %TARGET_MONTH%_raw_data.csv
if errorlevel 1 (
    echo [エラー] STEP 1 で失敗しました。
    pause
    exit /b
)

echo.
echo ------------------------------------------------------
echo [STEP 2] 労務費・経費按分 (allocate_costs.py) 実行中...
echo ------------------------------------------------------
%PYTHON% allocate_costs.py --month %TARGET_MONTH% --data %TARGET_MONTH%_raw_data.csv
if errorlevel 1 (
    echo [エラー] STEP 2 で失敗しました。
    pause
    exit /b
)

echo.
echo ======================================================
echo   全ての按分処理が正常に完了しました。
echo ======================================================
pause
exit /b

REM === エラー時専用のジャンプ先 ===
:MISSING_ERROR
echo ------------------------------------------------------
echo.
echo [中止] 必要なファイルが不足しています。
echo フォルダを確認して、ファイルを配置してから再実行してください。
pause
exit /b
