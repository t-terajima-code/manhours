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
echo   【工数集計】経理提出用データ作成プロセス
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
echo.

REM ログファイルの準備
set LOG_FILE=..\results\%TARGET_MONTH%_run_process_log.txt
echo ====== run_process.bat [%TARGET_MONTH%] %date% %time% ====== > %LOG_FILE%

echo ------------------------------------------------------
echo [STEP 1] 全担当者データの集計 (aggregate_hours.py)
echo ------------------------------------------------------
echo 全担当者データの集計を実行しますか?
set /p _YN_=
if errorlevel 2 goto SKIP_STEP1

echo [STEP 1] aggregate_hours.py >> %LOG_FILE%
%PYTHON% aggregate_hours.py --env env --month %TARGET_MONTH% 2>&1 | powershell -NoProfile -Command "& { $input | Tee-Object -Append -FilePath '%LOG_FILE%' }"
if errorlevel 1 (
    echo [エラー] STEP 1 【データの集計】 で失敗しました。
    pause
    exit /b
)
:SKIP_STEP1
echo.

echo ------------------------------------------------------
echo [STEP 2] 勤怠データと工数データの整合性を検証します...
echo ------------------------------------------------------
echo 検証処理を実行しますか?
set /p _YN_=
if errorlevel 2 goto SKIP_STEP2

echo 許容誤差(%%)を入力してください(例: 1.0):
set /p THRESHOLD=

echo [STEP 2] verify_hours.py --threshold %THRESHOLD% >> %LOG_FILE%
%PYTHON% verify_hours.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv --threshold %THRESHOLD% 2>&1 | powershell -NoProfile -Command "& { $input | Tee-Object -Append -FilePath '%LOG_FILE%' }"
if errorlevel 1 (
    echo [エラー] STEP 2 【検証処理】 で失敗しました。
    pause
    exit /b
)
:SKIP_STEP2
echo.
echo ======================================================
echo   検証結果を確認してください。
echo   NGが出ている場合は、個人のCSVを修正する必要があります。
echo ======================================================
echo.

echo ------------------------------------------------------
echo [STEP 3] 経理用CSVのエクスポート
echo ------------------------------------------------------
echo 検証結果はOKでしたか？経理用CSVを出力しますか?
set /p _YN_=
if errorlevel 2 (
    echo [スキップ] 経理用CSVの出力をスキップします。
    goto SKIP_STEP3
)

echo [STEP 3] export_keiri_csv.py >> %LOG_FILE%
%PYTHON% export_keiri_csv.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv 2>&1 | powershell -NoProfile -Command "& { $input | Tee-Object -Append -FilePath '%LOG_FILE%' }"
if errorlevel 1 (
    echo [エラー] STEP 3 【経理用CSV出力】 で失敗しました。
    pause
    exit /b
)
:SKIP_STEP3
echo.

echo ------------------------------------------------------
echo [STEP 4] 実働時間の按分 (allocate_actual_hours.py)
echo ------------------------------------------------------
echo 実働時間の按分計算を実行しますか?
set /p _YN_=
if errorlevel 2 goto SKIP_STEP4

echo [STEP 4] allocate_actual_hours.py >> %LOG_FILE%
%PYTHON% allocate_actual_hours.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv 2>&1 | powershell -NoProfile -Command "& { $input | Tee-Object -Append -FilePath '%LOG_FILE%' }"
if errorlevel 1 (
    echo [エラー] STEP 4 【実働時間の按分】 で失敗しました。
    pause
    exit /b
)
:SKIP_STEP4
echo.

echo ------------------------------------------------------
echo [STEP 5] 人工数および人員比率の算出 (calculate_person_months.py)
echo ------------------------------------------------------
echo 人工数および人員比率の算出を実行しますか?
set /p _YN_=
if errorlevel 2 goto SKIP_STEP5

echo [STEP 5] calculate_person_months.py >> %LOG_FILE%
%PYTHON% calculate_person_months.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv 2>&1 | powershell -NoProfile -Command "& { $input | Tee-Object -Append -FilePath '%LOG_FILE%' }"
if errorlevel 1 (
    echo [エラー] STEP 5 【人工数算出】 で失敗しました。
    pause
    exit /b
)
:SKIP_STEP5
echo.

echo ======================================================
echo   全プロセスが完了しました。
echo   ログ: %LOG_FILE%
echo ======================================================
pause
