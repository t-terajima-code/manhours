# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
