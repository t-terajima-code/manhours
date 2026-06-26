# -*- coding: utf-8 -*-
import pytest
import os
import sys
import datetime
import tempfile

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

# 各スクリプトから関数をインポート
import aggregate_hours
from aggregate_hours import (
    parse_env_file,
    excel_date_to_month,
    extract_person_name,
    check_unit_sanity,
    MAX_DAILY_MINUTES,
    MIN_MONTHLY_HOURS,
)

class TestExcelDateToMonth:
    """excel_date_to_month() 関数のテスト"""

    def test_valid_excel_date(self):
        """正常系: 有効なExcelシリアル値"""
        # 44000 = 2020/6/19
        result = excel_date_to_month('44000')
        assert result == '2020/06'

    def test_excel_date_epoch(self):
        """エッジケース: Excelシリアル値の基準日付"""
        # 1 = 1899/12/31
        result = excel_date_to_month('1')
        assert result == '1899/12'

    def test_float_excel_date(self):
        """エッジケース: 浮動小数点数入力"""
        result = excel_date_to_month('44000.5')
        assert result == '2020/06'

    def test_invalid_excel_date(self):
        """エラーケース: 無効な値"""
        result = excel_date_to_month('invalid')
        assert result is None

    def test_empty_string(self):
        """エラーケース: 空文字列"""
        result = excel_date_to_month('')
        assert result is None

    def test_negative_number(self):
        """エラーケース: 負の数"""
        result = excel_date_to_month('-1')
        assert result == '1899/12'

class TestExtractPersonName:
    """extract_person_name() 関数のテスト"""

    def test_pattern_yyyymm_prefix(self):
        """正常系: YYYYMMプレフィックス付き（新形式）"""
        result = extract_person_name('202504_A青山裕樹.csv')
        assert result == '青山裕樹'

    def test_pattern_yyyymm_prefix_variant(self):
        """正常系: YYYYMMプレフィックス付き別担当者"""
        result = extract_person_name('202603_T平杜夢.csv')
        assert result == '平杜夢'

    def test_no_extension(self):
        """エッジケース: 拡張子なし"""
        result = extract_person_name('_W渡邊聖')
        assert result == '渡邊聖'

    def test_no_underscore(self):
        """エッジケース: 英字と数字のみの名前"""
        # user_nameの場合、最後のアンダースコアで分割されて"name"が処理対象
        # 正規表現で全て英字が削除されるため、空文字列になる
        result = extract_person_name('user_name.csv')
        assert result == ''

    def test_multiple_underscores(self):
        """エッジケース: 複数のアンダースコア"""
        result = extract_person_name('_A_B_C太郎.csv')
        assert result == '太郎'

    def test_no_japanese(self):
        """エッジケース: 日本語なし"""
        # _Wtestの場合、testが全て英字なので、正規表現で全て削除される
        result = extract_person_name('_Wtest.csv')
        assert result == ''

class TestParseEnvFile:
    """parse_env_file() 関数のテスト"""

    def test_valid_env_file(self, sample_env_file, temp_project_dir):
        """正常系: 有効なenvファイル"""
        staff_dir, output_dir, master_dir = parse_env_file(sample_env_file)
        assert staff_dir == temp_project_dir['member_dir']
        assert output_dir == temp_project_dir['results_dir']
        assert master_dir == temp_project_dir['list_dir']

    def test_env_file_not_found(self):
        """エラーケース: ファイルが存在しない"""
        with pytest.raises(FileNotFoundError):
            parse_env_file('/nonexistent/path/env')

    def test_env_file_insufficient_lines(self):
        """エラーケース: 行数が不足"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='cp932', delete=False, suffix='.env') as f:
            f.write('line1\n')
            f.write('line2\n')
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                parse_env_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_env_file_with_backslash(self):
        """エッジケース: バックスラッシュ付きパス"""
        with tempfile.TemporaryDirectory() as tmpdir:
            member_dir = os.path.join(tmpdir, 'member')
            list_dir = os.path.join(tmpdir, 'list')
            results_dir = os.path.join(tmpdir, 'results')
            os.makedirs(member_dir)
            os.makedirs(list_dir)
            os.makedirs(results_dir)

            env_path = os.path.join(tmpdir, 'env')
            with open(env_path, 'w', encoding='cp932') as f:
                f.write(tmpdir + '\n')
                f.write('dummy1\n')
                f.write('\\member\n')
                f.write('dummy2\n')
                f.write('\\list\n')
                f.write('dummy3\n')
                f.write('\\results\n')
                f.write('dummy4\n')

            staff_dir, output_dir, master_dir = parse_env_file(env_path)
            assert staff_dir == member_dir
            assert output_dir == results_dir
            assert master_dir == list_dir

class TestIntegration:
    """統合テスト"""

    def test_full_flow_with_sample_data(self, sample_env_file, sample_staff_csv,
                                       sample_nichijou_csv, sample_proj_csv):
        """正常系: サンプルデータでの全処理フロー"""
        staff_dir, output_dir, master_dir = parse_env_file(sample_env_file)

        # ディレクトリが正しく解析されたことを確認
        assert os.path.exists(staff_dir)
        assert os.path.exists(output_dir)
        assert os.path.exists(master_dir)

        # マスタCSVが存在することを確認
        assert os.path.exists(os.path.join(master_dir, 'test_nichijou_list.csv'))
        assert os.path.exists(os.path.join(master_dir, 'test_proj_list.csv'))

        # 担当者CSVが存在することを確認
        assert os.path.exists(os.path.join(staff_dir, '202006_T_test_user.csv'))


# ===========================================================================
# ロバスト性実装(B): エンコード安全読込 / 単位サニティ警告
#   - fixture は本ファイル内にローカル定義（conftest は触らない）
#   - tempfile + CP932 で実構造に近い member/list/env を生成
# ===========================================================================
import csv
import glob
import contextlib
import io


# --- check_unit_sanity() の純粋関数テスト（fixture不要） -------------------

class TestCheckUnitSanity:
    """check_unit_sanity() のユニットテスト"""

    def test_no_warnings_for_normal(self):
        """正常系: 妥当な値なら警告ゼロ"""
        daily = {('2026/04', '太郎', '46113'): 480.0}      # 8時間=480分
        monthly = {('2026/04', '太郎'): 160.0}             # 月160時間
        assert check_unit_sanity(daily, monthly) == []

    def test_daily_over_24h_warns(self):
        """異常系: 日合計が1440分超で警告"""
        daily = {('2026/04', '太郎', '46113'): 1500.0}
        monthly = {('2026/04', '太郎'): 25.0}
        warnings = check_unit_sanity(daily, monthly)
        assert len(warnings) == 1
        assert '太郎' in warnings[0]
        assert '過大' in warnings[0]

    def test_daily_exactly_24h_no_warn(self):
        """境界: ちょうど1440分は警告しない（> 判定）"""
        daily = {('2026/04', '太郎', '46113'): MAX_DAILY_MINUTES}
        monthly = {('2026/04', '太郎'): 24.0}
        assert check_unit_sanity(daily, monthly) == []

    def test_monthly_too_small_warns(self):
        """異常系: 月合計が1h未満かつ>0で警告（時間入力による縮小の疑い）"""
        daily = {('2026/04', '太郎', '46113'): 8.0}        # 8分扱い
        monthly = {('2026/04', '太郎'): 8.0 / 60.0}        # 0.133時間
        warnings = check_unit_sanity(daily, monthly)
        assert len(warnings) == 1
        assert '過小' in warnings[0]

    def test_monthly_zero_no_warn(self):
        """境界: 月合計0は警告しない（>0 条件）"""
        daily = {}
        monthly = {('2026/04', '太郎'): 0.0}
        assert check_unit_sanity(daily, monthly) == []

    def test_monthly_exactly_1h_no_warn(self):
        """境界: ちょうど1時間は警告しない（< 判定）"""
        daily = {}
        monthly = {('2026/04', '太郎'): MIN_MONTHLY_HOURS}
        assert check_unit_sanity(daily, monthly) == []


# --- main() 統合用のローカルfixture / ヘルパ -------------------------------

def _make_env(tmpdir):
    """tmpdir 配下に member/list/results を作り、CP932 の env を返す。"""
    member_dir = os.path.join(tmpdir, 'member')
    list_dir = os.path.join(tmpdir, 'list')
    results_dir = os.path.join(tmpdir, 'results')
    os.makedirs(member_dir, exist_ok=True)
    os.makedirs(list_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    env_path = os.path.join(tmpdir, 'env')
    with open(env_path, 'w', encoding='cp932') as f:
        f.write(tmpdir + '\n')
        f.write('dummy1\n')
        f.write('member\n')
        f.write('dummy2\n')
        f.write('list\n')
        f.write('dummy3\n')
        f.write('results\n')
        f.write('7.5\n')
    return env_path, member_dir, list_dir, results_dir


def _write_masters(list_dir, fiscal_year):
    """期別マスタ3種を CP932 で作成（aggregate_hours が require する3ファイル）。
    日常業務マスタに業務名 'テスト業務' を1件登録しておく。"""
    # nichijou_list: key_col=2(業務名), val_cols=(0,1)
    with open(os.path.join(list_dir, f'{fiscal_year}_nichijou_list.csv'),
              'w', encoding='cp932', newline='') as f:
        w = csv.writer(f)
        w.writerow(['内外製', '品区', '業務名'])
        w.writerow(['N', 'n1', 'テスト業務'])
    # proj_list: key_col=0, val_cols=(2,3)
    with open(os.path.join(list_dir, f'{fiscal_year}_proj_list.csv'),
              'w', encoding='cp932', newline='') as f:
        w = csv.writer(f)
        w.writerow(['コード', '部課', '内外製', '品区'])
        w.writerow(['189001', '営業', 'G', 'g1'])
    # inc_list: key_col=0, val_cols=(1,2)
    with open(os.path.join(list_dir, f'{fiscal_year}_inc_list.csv'),
              'w', encoding='cp932', newline='') as f:
        w = csv.writer(f)
        w.writerow(['コード', '内外製', '品区'])
        w.writerow(['189054', 'K', 'k1'])


def _write_member_cp932(member_dir, fname, rows):
    """member CSV を CP932 で作成。rows は全行（ヘッダ2行含む）のリスト。"""
    path = os.path.join(member_dir, fname)
    with open(path, 'w', encoding='cp932', newline='') as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)
    return path


def _write_member_utf8(member_dir, fname, rows):
    """member CSV を UTF-8(BOM付き) で作成（誤保存を再現）。
    CP932で復号不能な文字（全角）を含めることで UnicodeDecodeError を誘発する。"""
    path = os.path.join(member_dir, fname)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)
    return path


def _member_rows_for_month(serial, value):
    """2026/04 内のExcelシリアル日付を使った member 行を組み立てる。
    row0=業務名(col2='テスト業務'), row1=コード(空), 以降=日付/曜日/値。"""
    return [
        ['date', 'holiday', 'テスト業務'],
        ['', '', ''],
        [str(serial), '水', str(value)],
    ]


# 2026/04 のExcelシリアル: 2026/04/01 = 46113
SERIAL_20260401 = 46113


def _run_main(env_path, month='202604', strict=False):
    """sys.argv を差し替えて aggregate_hours.main() を実行し、stdoutを返す。"""
    argv = ['aggregate_hours.py', '--env', env_path, '--month', month]
    if strict:
        argv.append('--strict')
    old_argv = sys.argv
    sys.argv = argv
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            aggregate_hours.main()
    finally:
        sys.argv = old_argv
    return buf.getvalue()


class TestEncodeSafeRead:
    """エンコード安全読込のテスト"""

    def test_default_skips_utf8_file_with_warning(self):
        """既定: UTF-8(BOM)誤保存ファイルはスキップし、警告サマリにファイル名が出る。
        正常なCP932ファイルの集計は完了する。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            # 正常CP932ファイル（480分=8時間）
            _write_member_cp932(member_dir, '202604_T正常.csv',
                                 _member_rows_for_month(SERIAL_20260401, 480))
            # UTF-8誤保存ファイル
            _write_member_utf8(member_dir, '202604_U不正.csv',
                               _member_rows_for_month(SERIAL_20260401, 480))

            out = _run_main(env_path, month='202604', strict=False)

            # スキップ警告に不正ファイル名が含まれる
            assert '202604_U不正.csv' in out
            assert 'スキップ' in out
            # 出力が生成され、正常担当者のみ列に含まれる
            out_file = os.path.join(results_dir, '202604_raw_data.csv')
            assert os.path.exists(out_file)
            with open(out_file, 'r', encoding='cp932', newline='') as f:
                header = next(csv.reader(f))
            assert '正常' in header
            assert '不正' not in header

    def test_strict_exits_nonzero_on_utf8(self):
        """--strict: UTF-8誤保存があれば sys.exit(1) で非ゼロ終了する。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            _write_member_utf8(member_dir, '202604_U不正.csv',
                               _member_rows_for_month(SERIAL_20260401, 480))

            with pytest.raises(SystemExit) as ei:
                _run_main(env_path, month='202604', strict=True)
            assert ei.value.code == 1

    def test_all_cp932_no_skip_warning(self):
        """正常系: 全ファイルCP932ならスキップ警告は出ない。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            _write_member_cp932(member_dir, '202604_T正常.csv',
                                 _member_rows_for_month(SERIAL_20260401, 480))

            out = _run_main(env_path, month='202604', strict=False)
            assert 'スキップしました' not in out


class TestUnitSanityInMain:
    """main() 経由での単位サニティ警告の発火/非発火"""

    def test_normal_no_sanity_warning(self):
        """正常系(8時間=480分): 単位サニティ警告は出ない。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            _write_member_cp932(member_dir, '202604_T正常.csv',
                                 _member_rows_for_month(SERIAL_20260401, 480))
            out = _run_main(env_path, month='202604', strict=False)
            assert '単位に異常' not in out

    def test_daily_over_24h_fires(self):
        """異常系: 1日2000分(>1440)入力で過大警告が発火。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            _write_member_cp932(member_dir, '202604_T過大.csv',
                                 _member_rows_for_month(SERIAL_20260401, 2000))
            out = _run_main(env_path, month='202604', strict=False)
            assert '単位に異常' in out
            assert '過大' in out

    def test_monthly_too_small_fires(self):
        """異常系: 「時間」入力(8 → /60で0.133h)で過小警告が発火。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            _write_member_cp932(member_dir, '202604_T過小.csv',
                                 _member_rows_for_month(SERIAL_20260401, 8))
            out = _run_main(env_path, month='202604', strict=False)
            assert '単位に異常' in out
            assert '過小' in out

    def test_sanity_does_not_block_output(self):
        """サニティ警告が出ても出力は通常通り生成される（strictでもブロックしない）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path, member_dir, list_dir, results_dir = _make_env(tmpdir)
            _write_masters(list_dir, 189)
            _write_member_cp932(member_dir, '202604_T過大.csv',
                                 _member_rows_for_month(SERIAL_20260401, 2000))
            out = _run_main(env_path, month='202604', strict=True)
            assert os.path.exists(os.path.join(results_dir, '202604_raw_data.csv'))
