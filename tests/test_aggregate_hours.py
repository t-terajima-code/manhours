# -*- coding: utf-8 -*-
import pytest
import os
import sys
import datetime
import tempfile

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

# 各スクリプトから関数をインポート
from aggregate_hours import (
    parse_env_file,
    excel_date_to_month,
    extract_person_name
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
