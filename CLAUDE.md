# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## エージェント実行順序（コード／ダッシュボード修正時の必須フロー）
コード・ダッシュボードを修正したら以下を回す。**進行管理とファイル修正の割り振りはオーケストレーター（メイン）が行う。**

1. **code-reviewer（レビュー専用・自身は一切修正しない）** → 指摘を出す。問題なければ REVIEW_COMPLETE。
2. code-reviewer が問題を報告したら、**メインが修正担当サブエージェントへ指示を出す**（code-reviewer には修正させない）：
   - コード／按分／ダッシュボードの修正 → **`manhours-cost-allocator`**
   - ドキュメント（README / docstring / マニュアル）の修正 → **`doc-writer`**
   修正が入ったら再度 code-reviewer に掛ける。
3. REVIEW_COMPLETE 後 → **doc-writer**（DOC_COMPLETE まで）
4. → **qa-tester**（QA_PASSED まで）。QA_FAILED の指摘も同様にメインが上記の担当へ振り、1 から回し直す。

QA_PASSED 後に配布用ZIPを作成する。

### ループ回数の上限
- **全体で最大5回まで**（「code-reviewer 起動 → 修正 → 再レビュー」の周回、および QA_FAILED による回し直しを合算して数える）。
- 5回で QA_PASSED に到達しない場合は、**未解決の指摘を列挙して停止し、メインがユーザーに報告**する（無限ループ禁止）。

### 修正担当の固定（重要）
- **code-reviewer は読み取り専用。ファイルを書き換えない。** 指摘の起票（場所・内容・重大度・推奨修正案・振り先）のみ。
- 実際の修正は必ず **`manhours-cost-allocator`（コード）** または **`doc-writer`（ドキュメント）** が、メインの指示で行う。
- code-reviewer はセキュリティ（プロンプトインジェクション／埋め込まれた悪意あるコード）も検査する。

### 対象とトリガー
- **`manhours-cost-allocator` が起動したら、必ずこのループに乗せること（例外なし）。** 按分ロジック・ダッシュボードの実装は cost-allocator が担当するが、その作業は単体で完了とはみなさず 1→4 を QA_PASSED まで回す。
- **ダッシュボード修正も同じループの対象（例外なし）。** 対象は `dashboard/` 一式（`index.html` / `js/dashboard.js` / `css/dashboard.css` / `data/data.js`）と `bin/generate_dashboard_data.py`。直接編集でも cost-allocator 経由でも必ずループへ。`generate_dashboard_data.py` → `data/data.js` を変更したら qa-tester で再生成と表示整合まで確認する。

サブエージェント定義は `.claude/agents/` に配置（`code-reviewer.md` / `doc-writer.md` / `qa-tester.md` / `manhours-cost-allocator.md`）。
（個人環境では `manhours-cost-allocator` 完了時のリマインド等を `.claude/settings.local.json` のフックで補助している場合がある。）

---

## Project Overview

**工数集計・按分システム (manhours)** - A Python-based system for collecting, validating, and allocating employee work hours across projects, with cost distribution based on financial data from accounting teams.

**Core workflow**: Employee hours → Aggregation → Validation → Distribution → Cost allocation → Financial export

**Key characteristic**: **2-stage processing model** (see "Operational Schedule" below)

---

## Directory Structure

```
bin/                    # 12 main processing scripts
  ├── aggregate_hours.py          # Collect work hours by project/assignee
  ├── verify_hours.py             # Validate against attendance data
  ├── allocate_actual_hours.py    # Allocate by actual working hours
  ├── allocate_costs.py           # Allocate costs by workload ratios
  ├── calculate_person_months.py  # Calculate person-months
  ├── export_keiri_csv.py         # Export accounting data
  ├── rearrange_person.py         # Unify employee info
  ├── update_data.py              # Data updates
  ├── run_process.bat             # Stage 1 execution script
  ├── run_allocate_costs.bat      # Stage 2 execution script
  └── gen_bat.py, make_*.py       # Batch file generators (low priority)

tests/                  # 167 pytest tests (100% passing, ~77-80% coverage)
  ├── conftest.py                 # 27+ shared fixtures (CSV, Excel, env)
  ├── test_aggregate_hours.py     # 22 tests, 88% coverage
  ├── test_allocate_costs.py      # 25 tests, 85% coverage
  └── test_*.py                   # Other module tests

list/                   # Master data (CSV format, CP932)
  ├── *_proj_list.csv            # Project definitions
  ├── hinku_list.csv              # Quality tier codes
  ├── *_person_all_list.csv       # Employee roster
  └── nichijou_list.csv           # Daily task definitions

member/, kintai/, soneki/, results/, keiri/  # Monthly data directories

OPERATION_MANUAL.md     # Operational guide for data aggregators (集計担当者向け)
REQUIREMENTS.md         # System requirements & architecture
```

---

## 配布パッケージ構成 (Distribution Packaging)

運用者（集計担当者）へ配付する ZIP の標準構成。最新のフル構成版は
`manhours_dist_full_YYYYMMDD.zip`（生成元フォルダ `manhours_dist_full_YYYYMMDD/`）。

### 同梱するフォルダ・ファイル

```
manhours_dist_full_YYYYMMDD/
├── bin/                 # 運用スクリプト + バッチ + env（下記「同梱する bin」参照）
├── list/               # マスタ一式（_backup* / _generated は除外）
├── member/             # 入力：月次工数 CSV（担当者別, CP932）
├── kintai/             # 入力：勤怠 xls（YYYYMM_kintai.xls ＋ 年度サブフォルダ）
├── soneki/             # 入力：損益 Excel（事業部別損益表_188/189.xlsx）。Stage 2 用
├── results/            # 出力：raw_data / allocated_hours / allocated_costs / person_months / keiri_ratio（見本同梱）
├── keiri/              # 出力：YYYYMM_keiri_ratio.csv（経理提出用・最終成果物。見本同梱）
├── dashboard/          # KPI ダッシュボード一式（index.html, css/, js/, data/data.js）
├── input_ui/           # 工数入力 UI（完成 HTML のみ：工数入力.html, インシデント管理表.html, README.md）
├── docs/               # マニュアル：OPERATION_MANUAL.md/.html, REQUIREMENTS.md, 運用マニュアル PDF 各種
└── requirements.txt
```

### 同梱する bin（運用サブセット）
`aggregate_hours.py` / `verify_hours.py` / `allocate_actual_hours.py` /
`calculate_person_months.py` / `export_keiri_csv.py` / `allocate_costs.py` /
`rearrange_person.py` / `update_data.py` / `generate_dashboard_data.py` /
`make_env.py`（env 再生成。OPERATION_MANUAL の初回セットアップ手順で参照） /
`env` / `run_process.bat` / `run_allocate_costs.bat` / `run_all.bat`

### 配布から除外するもの
- **bin の開発・生成系**: `make_bat.py` / `gen_bat.py` / `make_run_all.py` /
  `make_run_process.py` / `make_inc_list.py` / `build_inc_*.py` / `derive_inc_list.py` /
  `md_to_html.py` / `_send_zip.py` / `input.txt` / `input_test.txt` / `__pycache__/` /
  `run_process_test.bat`
- **list**: `_backup_*` / `_generated`
- **kintai**: `make_dummy_kintai.py`（ダミー勤怠生成の開発用。個人名ハードコードあり）
- **soneki**: `test_csv` 等のテストデータ
- **input_ui**: 再生成素材（`_template.html` / `_master_data.json` / `_inc_master_data.json` /
  `encoding.min.js` / `build_master.py` / `build_inc_master.py`）
- **ルート文書**: `CLAUDE.md`, `*作成プロンプト.md`, `TEST_GUIDE.md`, `TEST_REPORT.md`, テスト一式（`tests/`）

### 注意点
- **`bin/env` の1行目**は絶対パス（開発環境）。別環境へ展開する場合は展開先パスへ要書き換え。
- 配付前に `python bin/make_bat.py --check` で bat 群がソースとバイト一致するか検証する。
- マスタ更新時は `input_ui/工数入力.html` を再生成（手順は `input_ui/README.md`）。

---

## Common Commands

### Running Tests
```bash
# All tests with coverage
pytest tests/ --cov=bin --cov-report=term-missing

# Single module tests
pytest tests/test_aggregate_hours.py -v

# Single test function
pytest tests/test_allocate_costs.py::TestGetSonekiCosts::test_valid_soneki_xlsx -v

# Run with output
pytest tests/ -s
```

### Running Scripts
```bash
# For development/debugging (Windows)
cd bin
python aggregate_hours.py --env env --month 202604

# Batch execution (operational)
bin\run_process.bat           # Stage 1: aggregation + validation
bin\run_allocate_costs.bat    # Stage 2: cost allocation
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Check imports are working
python -c "import openpyxl, pandas; print('OK')"
```

---

## Architecture & Data Flow

### 2-Stage Operational Model (CRITICAL)

This system uses **mandatory 2-stage processing** aligned with business calendar:

**Stage 1 (Within 5 business days of month start)**
- Script: `run_process.bat`
- Processes: aggregate_hours → verify_hours → allocate_actual_hours → calculate_person_months → export_keiri_csv
- Output: `raw_data.csv`, `YYYYMM_actual_hours.csv`
- Purpose: Early error detection (工数エラー検出)
- Then: Wait for accounting team's financial data

**Stage 2 (Days 15-25, when accounting provides financial Excel)**
- Script: `run_allocate_costs.bat`
- Processes: allocate_actual_hours (re-run) → allocate_costs
- Input: `raw_data.csv` + `soneki/soneki_YYYYMM.xlsx` (loss/profit Excel from accounting)
- Output: `keiri_YYYYMM.csv` (final accounting export)
- Purpose: Allocate costs using latest financial data

**Key insight**: Stage 2 timing (15-25日) varies monthly depending on accounting's financial close schedule. This is not a fixed date—it's trigger-driven by "financial data arrived" notification.

### Data Pipeline (Stage 1)

```
member/*.csv (employee hours)
    ↓
aggregate_hours.py
    ↓
raw_data.csv (hours by project × assignee)
    ↓
verify_hours.py + kintai/*.html (attendance validation)
    ↓
allocate_actual_hours.py (scale by actual working hours)
    ↓
YYYYMM_actual_hours.csv
    ↓
calculate_person_months.py (convert to person-months)
    ↓
export_keiri_csv.py (preliminary export)
```

### Data Pipeline (Stage 2)

```
raw_data.csv + soneki/soneki_YYYYMM.xlsx (accounting's financial data)
    ↓
allocate_costs.py (allocate labor costs & expenses by hour ratio)
    ↓
YYYYMM_allocated_costs.csv → keiri_YYYYMM.csv (final accounting export)
```

### Record Filtering Logic (Important)

All pipelines filter by `naigai` (internal/external classification) and `hinku` (quality tier):

```python
# In aggregate_hours.py, allocate_costs.py, etc.
def is_target_record(naigai, hinku):
    if naigai in ['N', 'G', 'K']: return True  # Always include
    if naigai == 'y' and hinku in ['y1', 'y10', 'y20']: return True  # Conditional
    return False
```

This filtering applies across all aggregation steps.

---

## Critical Technical Constraints

### 1. File Encoding (Absolute Requirement)
- **Input/Output CSV**: CP932 (Windows Japanese encoding)
- **Attendance HTML**: UTF-8
- **Excel**: XLSX only (openpyxl)
- **Configuration env files**: CP932

**Why**: All files are processed on Windows, employee names contain Japanese characters. Encoding mismatch causes "character garble" (文字化け) errors.

**When modifying CSV I/O**: Always specify `encoding='cp932'` in pandas/csv operations.

### 2. Date Format Handling
- **Internal**: `YYYY/MM` format (e.g., `2026/04`)
- **Input**: Excel serial dates or `YYYYMMDD` (e.g., `202604`)
- **Conversion**: `excel_date_to_month()` in aggregate_hours.py handles Excel serial → YYYY/MM

**When touching date logic**: Test with both formats explicitly.

### 3. Excel Sheet Names (allocate_costs.py dependency)
- soneki Excel files must have sheets named by month: `4月` (April), `5月` (May), etc.
- Logic extracts `YYYYMM` input → converts to month number → looks up sheet name
- Missing sheet for target month → ValueError raised

**When debugging cost allocation**: Check soneki Excel sheet names first.

### 4. Environment File (env) Structure
```
Line 1: Project root directory
Line 3: member/ subdirectory name
Line 5: list/ subdirectory name
Line 6: soneki/ subdirectory name (allocate_costs only)
Line 7: results/ subdirectory name
```
All scripts parse this to locate data directories. Format is rigid.

---

## Testing Strategy

### Fixture Architecture (conftest.py)
All test fixtures use `tempfile.TemporaryDirectory()` for isolation:
- `temp_project_dir`: Creates in-memory directory tree with subdirs
- `sample_*_file`: Generate test CSVs/Excel/env files dynamically
- Each fixture uses CP932 encoding for CSV files
- **Key pattern**: Fixtures create minimal valid data, not replicate production complexity

### Test Module Pattern
Each `test_*.py` covers one script's functions:
1. **Unit tests** for helper functions (parse_env_file, is_target_record, etc.)
   - Test normal cases, edge cases (empty input, whitespace, boundary values)
   - Test error cases (missing files, format errors)
2. **Main function tests** for script entry points
   - Mock `sys.argv` to simulate CLI arguments
   - Mock external calls (get_soneki_costs returns, print capture)
   - Verify output files generated
3. **Integration tests** for full workflows
   - Use real test data flowing through multiple steps
   - Verify final output correctness

### Running Tests Locally
- All 167 tests must pass before committing
- Target coverage: 70%+ per script (currently 85-98% for main modules)
- Use `pytest tests/ -v` for full output; `-x` stops on first failure
- Coverage gaps usually indicate untested error branches or rarely-used code paths

---

## Development Workflow

### When Adding Features
1. **Identify which script** needs the change (aggregate_hours.py? allocate_costs.py?)
2. **Extract logic to a testable function** (not inline in main()) if possible
3. **Add unit test** before implementing (TDD-style preferable)
4. **Update OPERATION_MANUAL.md** if it affects user-facing behavior
5. **Run full test suite** before committing: `pytest tests/ --cov=bin`
6. **Test in both batch modes** if touching Stage 1/2 logic

### When Fixing Bugs
- Reproduce with a test first
- Fix the bug
- Verify test passes
- Check no other tests regressed

### Git Commits
- Reference which script/module changed
- Note operational impact if user-facing (e.g., "affects Stage 2 output format")
- Include test additions/modifications in the same commit

---

## Common Pitfalls & Solutions

| Problem | Root Cause | Solution |
|---------|-----------|----------|
| "Character garble" in output CSV | Encoding mismatch | Use `encoding='cp932'` on all CSV write operations |
| allocate_costs.py fails "sheet not found" | Wrong month name in Excel (e.g., "April" vs "4月") | Verify soneki Excel uses Japanese month names |
| verify_hours.py returns no data | HTML parser mismatch or missing columns | Check attendance HTML table has name/hours columns |
| Tests fail in isolation but pass together | Fixture state pollution | Ensure fixtures use fresh temp directories (conftest already does) |
| run_process.bat hangs | Missing env file or wrong path | Check `bin\env` exists and points to valid directory |
| aggregate_hours produces all-zero output | No member CSV files found | Verify `member/` folder has `_W*` or `*_T*` named files |

---

## Important Notes for Future Work

### Test Data Maintenance
The test fixtures in `conftest.py` generate sample data on-the-fly. If you modify core CSV/Excel formats, update the corresponding fixture. For example:
- If `raw_data.csv` columns change → update `sample_raw_data_costs_csv` fixture
- If Excel sheet structure changes → update `sample_soneki_xlsx_costs` fixture

### Performance Considerations
- System currently handles up to ~100 employees per month (tested/documented)
- Processing time: Stage 1 ~5 min, Stage 2 ~2 min (on typical hardware)
- No database—everything is file-based CSV/Excel
- If data volume grows significantly, consider moving to database backend

### Operational Documentation
- **集計担当者向け** (Data aggregators): Read OPERATION_MANUAL.md (Japanese, no technical detail)
- **System owners**: Read REQUIREMENTS.md (system architecture, requirements)
- Slack/email operators should reference "Stage 1" and "Stage 2" terminology, not internal script names

### Batch Files (run_process.bat, run_allocate_costs.bat)
- Located in `bin/`
- Orchestrate multiple Python scripts with user prompts
- Handle month input validation
- Check for required input files before running
- **Do not modify script order or add/remove steps** without consulting operational team

---

## Recent Work (Session Context)

As of 2026-05-26:
- ✅ 167 comprehensive tests implemented (100% pass rate)
- ✅ OPERATION_MANUAL.md v2.0 (fully updated for 2-stage model with real dates)
- ✅ allocate_costs.py: 25 tests added, 85% coverage
- ✅ Distribution zip created (55 KB, tests excluded)
- ⚠️ Next priorities: Monitor Stage 2 execution; capture real loss/profit Excel edge cases

---

## Quick Reference: Running Month-End Process

```bash
# DAY 1-5: Stage 1
cd bin
run_process.bat
# Input: 202604
# Output: results/raw_data.csv, results/YYYYMM_actual_hours.csv
# Operator checks for errors; sends back to sender if issues found

# DAY 15-25: When accounting sends loss/profit Excel
# Place Excel in soneki/soneki_202604.xlsx

# Run Stage 2
run_allocate_costs.bat
# Input: 202604 (same as Stage 1)
# Output: keiri/keiri_202604.csv → submit to accounting team
```

---

**Last updated**: 2026-05-26  
**Operational model**: 2-stage (within 5 days + 15-25 days)
