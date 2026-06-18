@echo off
pushd "%~dp0"
setlocal enabledelayedexpansion

REM python コマンドが使えない場合は py にフォールバック
where python > nul 2>&1
if errorlevel 1 (
    set PYTHON=py
) else (
    set PYTHON=python
)

echo ======================================================
echo   労務費・経費按分プロセス
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
if !count! == 6 set "SONEKI_SUB=%%a"
if !count! == 7 set "RESULTS_SUB=%%a"
)

REM 先頭の \ を除去してパスを結合
set "SONEKI_DIR=!ROOT_DIR!\!SONEKI_SUB:\=!"
set "RESULTS_DIR=!ROOT_DIR!\!RESULTS_SUB:\=!"
echo.

echo --- ファイルの存在確認中 ---

echo [確認1] !RESULTS_DIR!\raw_data.csv
if not exist "!RESULTS_DIR!\raw_data.csv" (
echo [NG] 未検出: raw_data.csv
goto :MISSING_ERROR
)
echo [OK] 検出: raw_data.csv

echo [確認2] !SONEKI_DIR!\*.xlsx
if not exist "!SONEKI_DIR!\*.xlsx" (
echo [NG] 未検出: 損益データ [!SONEKI_DIR! 内]
goto :MISSING_ERROR
)
echo [OK] 検出: 損益データ

echo ------------------------------------------------------
echo 必要なファイルが揃いました。
echo ======================================================
echo.

REM メッセージと入力受付
echo 労務費・経費の按分処理を開始しますか?
choice /C YN /M "Yes(Y) / No(N)"
if errorlevel 2 (
echo.
echo [中止] ユーザにより処理がキャンセルされました。
pause
exit /b
)

echo.
echo 按分処理を実行中...
%PYTHON% allocate_costs.py --month "%TARGET_MONTH%"
if errorlevel 1 (
    echo.
    echo [エラー] 按分処理中にエラーが発生しました。
    pause
    exit /b
)

echo.
echo 全ての処理が完了しました。
pause
exit /b

:MISSING_ERROR
echo.
echo [エラー] 必要なファイルが見つかりません。確認して再度実行してください。
pause
exit /b
