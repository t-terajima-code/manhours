# -*- coding: utf-8 -*-
"""bin/ の運用バッチ (.bat) を CP932 + CRLF で再生成する正準スクリプト。

【役割】
このスクリプトが bin/ 配下の運用バッチの「唯一の正(source of truth)」。
誰かがエディタで .bat を UTF-8 保存し直して文字化けさせても、
このスクリプトを再実行すれば必ず正しい CP932 + CRLF の .bat に戻る。

【重要・エンコード事故の構造的再発防止】
  - 全 .bat は encoding='cp932'(Shift-JIS) で書き出す。cmd.exe の既定に一致。
  - 改行は CRLF(
) に統一(newline='' + 文字列内 
)。
  - 絵文字・chcp は使わない(CP932統一方針)。

【.bat の内容を変更したいとき】
  下の BATS 辞書(各バッチの全文)を編集し、本スクリプトを再実行すること。
  .bat を直接手編集しない。手編集してもこのスクリプト再実行で上書きされる。

使い方:
    cd bin
    python make_bat.py            # 4本すべて再生成
    python make_bat.py --check    # 既存 .bat と一致するか検証(書き換えない)
"""
import argparse
import sys

# === 各運用バッチの全文(正) ===========================================
# ここが唯一の正。編集はここで行い、python make_bat.py を再実行する。
BATS = {}

BATS["run_process.bat"] = r"""@echo off
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

echo 対象の年月を入力してください (例: 202603):
set /p TARGET_MONTH=

if "%TARGET_MONTH%"=="" (
    echo [エラー] 年月が入力されていません。処理を終了します。
    pause
    exit /b
)
echo.

set LOG_FILE=../results/%TARGET_MONTH%_run_process_log.txt
set TMP_OUT=_tmp_step.txt
echo ====== run_process.bat [%TARGET_MONTH%] %date% %time% ====== > "%LOG_FILE%"

echo ------------------------------------------------------
echo [STEP 1] 全担当者データの集計 (aggregate_hours.py)
echo ------------------------------------------------------
echo 全担当者データの集計を実行しますか?
choice /C YN /M "Yes(Y) / No(N)"
if errorlevel 2 goto SKIP_STEP1

echo [STEP 1] aggregate_hours.py >> "%LOG_FILE%"
%PYTHON% aggregate_hours.py --env env --month %TARGET_MONTH% > %TMP_OUT% 2>&1
type %TMP_OUT%
type %TMP_OUT% >> "%LOG_FILE%"
erase %TMP_OUT%
if errorlevel 1 (
    echo [エラー] STEP 1 【データの集計】 で失敗しました。
    pause
    exit /b
)
:SKIP_STEP1
echo.

echo ------------------------------------------------------
echo [STEP 2] 勤怠データと工数データの整合性を検証します
echo ------------------------------------------------------
echo 検証処理を実行しますか?
choice /C YN /M "Yes(Y) / No(N)"
if errorlevel 2 goto SKIP_STEP2

echo 許容誤差(%%)を入力してください(例: 1.0):
set /p THRESHOLD=

echo [STEP 2] verify_hours.py --threshold %THRESHOLD% >> "%LOG_FILE%"
%PYTHON% verify_hours.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv --threshold %THRESHOLD% > %TMP_OUT% 2>&1
type %TMP_OUT%
type %TMP_OUT% >> "%LOG_FILE%"
erase %TMP_OUT%
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
echo [STEP 3] 経理用CSVのエクスポート (export_keiri_csv.py)
echo ------------------------------------------------------
echo 検証結果はOKでしたか？経理用CSVを出力しますか?
choice /C YN /M "Yes(Y) / No(N)"
if errorlevel 2 (
    echo [スキップ] 経理用CSVの出力をスキップします。
    goto SKIP_STEP3
)

echo [STEP 3] export_keiri_csv.py >> "%LOG_FILE%"
%PYTHON% export_keiri_csv.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv > %TMP_OUT% 2>&1
type %TMP_OUT%
type %TMP_OUT% >> "%LOG_FILE%"
erase %TMP_OUT%
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
choice /C YN /M "Yes(Y) / No(N)"
if errorlevel 2 goto SKIP_STEP4

echo [STEP 4] allocate_actual_hours.py >> "%LOG_FILE%"
%PYTHON% allocate_actual_hours.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv > %TMP_OUT% 2>&1
type %TMP_OUT%
type %TMP_OUT% >> "%LOG_FILE%"
erase %TMP_OUT%
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
choice /C YN /M "Yes(Y) / No(N)"
if errorlevel 2 goto SKIP_STEP5

echo [STEP 5] calculate_person_months.py >> "%LOG_FILE%"
%PYTHON% calculate_person_months.py --month %TARGET_MONTH% --env env --data %TARGET_MONTH%_raw_data.csv > %TMP_OUT% 2>&1
type %TMP_OUT%
type %TMP_OUT% >> "%LOG_FILE%"
erase %TMP_OUT%
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
"""

BATS["run_all.bat"] = r"""@echo off
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
"""

BATS["run_allocate_costs.bat"] = r"""@echo off
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

REM env 1行目が実在しなければパッケージルート(このbatの親)を使う（別PC/別ドライブ対応・Python側と整合）
if not exist "!ROOT_DIR!\" set "ROOT_DIR=%~dp0.."

REM 先頭の \ を除去してパスを結合
set "SONEKI_DIR=!ROOT_DIR!\!SONEKI_SUB:\=!"
set "RESULTS_DIR=!ROOT_DIR!\!RESULTS_SUB:\=!"
echo.

echo --- ファイルの存在確認中 ---

echo [確認1] !RESULTS_DIR!\%TARGET_MONTH%_raw_data.csv
if not exist "!RESULTS_DIR!\%TARGET_MONTH%_raw_data.csv" (
echo [NG] 未検出: %TARGET_MONTH%_raw_data.csv
goto :MISSING_ERROR
)
echo [OK] 検出: %TARGET_MONTH%_raw_data.csv

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
%PYTHON% allocate_costs.py --month "%TARGET_MONTH%" --data %TARGET_MONTH%_raw_data.csv
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
"""

BATS["run_process_test.bat"] = r"""@echo off
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
"""


# 末尾の改行を1つに正規化(raw文字列の都合で末尾改行が付くため)
for _name in list(BATS):
    BATS[_name] = BATS[_name].rstrip("\n") + "\n"


def _to_crlf(text):
    """LF を CRLF に統一する。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


def write_bats():
    """全 .bat を CP932 + CRLF で書き出す。"""
    for name, text in BATS.items():
        data = _to_crlf(text).encode("cp932")
        with open(name, "wb") as f:
            f.write(data)
        print(f"生成完了: {name} (CP932 + CRLF, {len(data)} bytes)")


def check_bats():
    """既存 .bat が生成内容とバイト一致するか検証する。"""
    import os
    ok = True
    for name, text in BATS.items():
        expected = _to_crlf(text).encode("cp932")
        if not os.path.exists(name):
            print(f"[NG] {name}: ファイルが存在しません")
            ok = False
            continue
        actual = open(name, "rb").read()
        if actual == expected:
            print(f"[OK] {name}: バイト一致")
        else:
            print(f"[NG] {name}: 不一致 (実体 {len(actual)} bytes / 期待 {len(expected)} bytes)")
            ok = False
    return ok


def main():
    parser = argparse.ArgumentParser(description="運用バッチを CP932+CRLF で再生成/検証")
    parser.add_argument("--check", action="store_true",
                        help="書き換えずに既存 .bat と一致するか検証する")
    args = parser.parse_args()
    if args.check:
        sys.exit(0 if check_bats() else 1)
    write_bats()


if __name__ == "__main__":
    main()
