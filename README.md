# 工数集計・按分システム (manhours)

毎月の従業員工数を集計・検証し、経理から提供される損益Excelに基づいてプロジェクトへ
労務費・経費を按分し、経理提出用CSVを出力するシステムです。

本READMEは開発者・運用者向けの入口（実行環境・手順・入出力・注意事項）をまとめたものです。

- 集計担当者向けの手順書: `OPERATION_MANUAL.md` / `OPERATION_MANUAL.html`
- システム要件・アーキテクチャ: `REQUIREMENTS.md`
- 開発ガイド（テスト・設計指針）: `CLAUDE.md`

---

## 1. 実行環境

- **OS**: Windows（業務データの氏名・CSVが CP932/Shift-JIS のため Windows 前提）
- **Python**: 3.9 以上（3.10〜3.12 で動作確認）
- **依存ライブラリ**: `requirements.txt` を参照（pandas / openpyxl / numpy はpandas同梱、テスト用に pytest, pytest-cov）

```bash
pip install -r requirements.txt
# 動作確認
python -c "import pandas, openpyxl; print('OK')"
```

> 💡 **`python` で動かない場合は `py` に読み替えてください**（例: `py -m pip install ...`、`py generate_dashboard_data.py`）。
> Microsoft Store 版のダミー `python` が入っている環境で起きることがあります。
> バッチ（`run_process.bat` / `run_allocate_costs.bat` / `run_all.bat`）は `py`／`python` を自動判定するため、この読み替えは不要です。

`requirements.txt` の主な内容:

| ライブラリ | 用途 |
|---|---|
| `pandas` | 損益Excel・各CSVの読み書き（numpy は依存として自動導入） |
| `openpyxl` | xlsx（損益Excel・インシデント管理表）の読み込み |
| `pytest` / `pytest-cov` | テスト実行・カバレッジ計測 |

---

## 2. 実行手順（2段階運用）

本システムは業務スケジュールに合わせた **2段階処理** です。バッチは `bin/` 内にあり、
ダブルクリック（または `bin\` で実行）すると対象年月（例: `202604`）の入力を促します。

```
【月初】稼働5日以内
  └─ run_process.bat   … 集計～検証～配分（工数エラーを月初に検出）

【15日～25日ごろ】損益Excel到着後
  └─ run_allocate_costs.bat … コスト按分（最新損益データを反映し経理提出）
```

### Stage 1: `bin\run_process.bat`

集計から各種配分までを対話形式（各STEPで Yes/No）で実行します。

| STEP | スクリプト | 内容 |
|---|---|---|
| 1 | `aggregate_hours.py` | member CSV を集計 → `results/{YYYYMM}_raw_data.csv` |
| 2 | `verify_hours.py` | 勤怠データと照合し工数エラーを検出（許容誤差%を入力） |
| 3 | `export_keiri_csv.py` | 経理提出用比率CSV → `results/{YYYYMM}_keiri_ratio.csv` |
| 4 | `allocate_actual_hours.py` | 実働時間ベースの按分 → `results/{YYYYMM}_allocated_hours.csv` |
| 5 | `calculate_person_months.py` | 人工数(PM)算出 → `results/{YYYYMM}_person_months.csv` |

ログは `results/{YYYYMM}_run_process_log.txt` に保存されます。STEP 2 でNGが出た場合は
入力元（担当者CSV）の修正が必要です。

### Stage 2: `bin\run_allocate_costs.bat`

経理から損益Excelが届いたら、`soneki/` に配置して実行します。

| スクリプト | 内容 |
|---|---|
| `allocate_costs.py` | 損益Excelの労務費・経費を工数比率で按分 → `results/{YYYYMM}_allocated_costs.csv` |

最終的な経理提出CSV（`{YYYYMM}_keiri_ratio.csv`）は `keiri/` に複製して提出します。

### 補助バッチ・スクリプト

- **`run_all.bat`**: 既に `{YYYYMM}_raw_data.csv`・勤怠・損益が揃っている前提で、
  `allocate_actual_hours.py` と `allocate_costs.py` を続けて実行する短縮バッチ。
  Stage 2を一括で回したいとき向け。
- **`generate_dashboard_data.py`**: `results/` のCSVを統合して
  `dashboard/data/data.js`（KPIダッシュボード用、UTF-8）を生成。`python generate_dashboard_data.py`。
  案件名（インシデント番号→案件名）は配布物同梱の `list/inc_name_list.csv` 優先で読み込むため、
  `インシデント管理表.xlsx` 非同梱の配布版でも案件名込みで再生成できます（xlsxはフォールバック）。
- **`derive_inc_list.py`**: `{期}_inc_master.csv` から検証用の `{期}_inc_list.csv` を
  `list/_generated/` へ派生生成（本番 list は上書きしない）。
- **`gen_bat.py` / `make_bat.py`**: バッチ4本を CP932+CRLF で再生成（`make_bat.py` が本体）。

> ℹ️ `derive_inc_list.py` / `gen_bat.py` / `make_bat.py` および inc マスタ生成系
> （`make_inc_list.py` 等）は **システム部門向けの開発・生成用ツール**です。
> 運用者向けの**配布版パッケージには同梱されません**（配布版は集計担当者が使う
> 運用スクリプトとマスタ・データのみを含みます）。

### 開発・デバッグ時の単体実行

```bash
cd bin
python aggregate_hours.py --env env --month 202604
python allocate_costs.py --env env --month 202604 --data 202604_raw_data.csv
```

### テスト

```bash
pytest tests/ --cov=bin --cov-report=term-missing
```

---

## 3. 入力ファイルの形式と配置場所

ディレクトリ構成は `bin/env` で定義します（下記「env と可搬性」を参照）。標準構成は以下です。

| ディレクトリ | 内容 | 形式・命名 |
|---|---|---|
| `member/` | 担当者ごとの工数CSV | CP932。`{YYYYMM}_*.csv`。1行目=業務名、2行目=インシデントコード、3行目以降=日付(Excelシリアル)×工数（**分単位入力**） |
| `kintai/` | 勤怠データ | UTF-8。`*{YYYYMM}*kintai*.xls`（HTMLテーブル形式）。実働時間・休暇列を含む |
| `soneki/` | 損益Excel（経理提供、Stage 2） | xlsx。ファイル名に期番号を含む。月別シート（`4月`,`5月`…）に「機能部間接部門費（労務費／経費）」の研究開発・全社実績金額 |
| `list/` | マスタCSV | CP932。`{期}_proj_list.csv` / `{期}_inc_list.csv` / `{期}_nichijou_list.csv` / `{期}_hinku_list.csv` 等（期=188,189…）。`inc_name_list.csv`（インシデント番号→案件名、ダッシュボード用）も同梱 |

補足:
- **工数は「分」入力**が前提です（システムが /60 で時間換算）。「時間」で入力すると
  値が1/60に縮むため、`aggregate_hours.py` が単位異常を警告します。
- 期番号（事業年度）は対象月から算出します（4月始まり。2025/4〜2026/3=188期、2026/4〜2027/3=189期）。
- 損益Excelのシート名が月名（例 `4月`）でないと `allocate_costs.py` が金額を抽出できません。

---

## 4. 出力ファイルの場所

すべての成果CSVは `results/` に CP932 で出力されます（`{YYYYMM}_` 接頭辞付き）。

| 出力ファイル | 生成元 | 内容 |
|---|---|---|
| `results/{YYYYMM}_raw_data.csv` | `aggregate_hours.py` | 月×案件×担当者の集計工数（時間換算後） |
| `results/{YYYYMM}_allocated_hours.csv` | `allocate_actual_hours.py` | 実働時間ベースの按分・休暇換算 |
| `results/{YYYYMM}_person_months.csv` | `calculate_person_months.py` | 案件別の人工数(PM)・個人比率・業務統計 |
| `results/{YYYYMM}_keiri_ratio.csv` | `export_keiri_csv.py` | 経理提出用の内外製×品区別 工数比率 |
| `results/{YYYYMM}_allocated_costs.csv` | `allocate_costs.py` | 労務費・経費・投入人員の按分結果 |
| `results/{YYYYMM}_run_process_log.txt` | `run_process.bat` | Stage 1 の実行ログ |

- **`keiri/`**: 経理へ提出する `{YYYYMM}_keiri_ratio.csv` の複製置き場。
- **`dashboard/data/data.js`**: `generate_dashboard_data.py` が生成するKPI用データ（**UTF-8**）。

---

## 5. 注意事項

### 個人情報の取り扱い

- `member/`・`kintai/`・`keiri/`・`soneki/`・`list/`・`results/` には社員氏名・勤怠・
  経理・損益などの **機密データ** が含まれます。これらは `.gitignore` で Git 追跡から
  除外しています（リポジトリにコミットしないこと）。
- 配布・共有時はこれらのデータディレクトリと `bin/env`、各種 Excel（`*.xls`/`*.xlsx`/`*.xlsm`）、
  ダッシュボードのスクリーンショット（`*.png`）を含めないよう注意してください。

### 文字コード（CP932）

- 入出力CSV・マスタ・`env` はすべて **CP932（Shift-JIS）** です。勤怠HTMLのみ UTF-8、
  `dashboard/data/data.js` のみ UTF-8。
- member CSV を Excel等で UTF-8/BOM付きで保存すると文字化け・読込失敗の原因になります。
  `aggregate_hours.py` は CP932 で読めないファイルを既定でスキップし警告します
  （`--strict` 指定時はエラー終了）。CSV を編集・追加する際は CP932 で保存してください。

### env の可搬性（別PC・別ドライブへの移動）

- 各スクリプトは `bin/env`（CP932・最低8行）でルートおよび member/list/soneki/results の
  サブディレクトリ名を解決します。
- **env の1行目（ルート絶対パス）が実在しない場合は、env の場所＝`bin/` の親ディレクトリ
  （パッケージルート）を自動採用してフォールバック**します。
  このため、パッケージ一式を別PC・別ドライブへ展開・移動しても env を書き換えずに動作します。
- 逆に、1行目に有効な絶対パスが書かれている場合はそれが優先されます。意図せず古いパスを
  指していると別の場所を読みに行くため、移設時は1行目を更新するか、無効値にしてフォールバックに
  委ねてください。

`bin/env` の行構成:

```
1行目: ルートディレクトリ（絶対パス。無効なら bin/ の親へ自動フォールバック）
2行目: \bin
3行目: \member
4行目: \kintai
5行目: \list
6行目: \soneki
7行目: \results
8行目: 標準勤務時間（h/日。例: 7.5）
```

---

## 6. ディレクトリ概要

```
bin/        … 処理スクリプト・バッチ・env
list/       … マスタCSV（CP932、機密）
member/     … 担当者工数CSV（機密）
kintai/     … 勤怠データ（機密）
soneki/     … 損益Excel（機密、Stage 2）
results/    … 出力CSV
keiri/      … 経理提出用CSVの複製
dashboard/  … KPIダッシュボード（data/data.js を生成）
tests/      … pytest テスト一式
```
