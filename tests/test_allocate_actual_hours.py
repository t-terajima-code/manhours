# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from allocate_actual_hours import (
    parse_env_file,
    get_kintai_name
)

class TestGetKintaiName:
    """get_kintai_name() 関数のテスト"""

    def test_exact_match(self):
        """正常系: 完全一致"""
        kintai_dict = {'営業部': 100, '企画部': 200}
        result = get_kintai_name(kintai_dict, '営業部')
        assert result == '営業部'

    def test_with_spaces(self):
        """エッジケース: スペース付き"""
        kintai_dict = {'営業部': 100}
        result = get_kintai_name(kintai_dict, ' 営 業 部 ')
        assert result == '営業部'

    def test_with_full_width_spaces(self):
        """エッジケース: 全角スペース付き"""
        kintai_dict = {'営業部': 100}
        result = get_kintai_name(kintai_dict, '　営　業　部　')
        assert result == '営業部'

    def test_partial_match(self):
        """エッジケース: 部分一致"""
        kintai_dict = {'営業部': 100}
        result = get_kintai_name(kintai_dict, '営業部企画')
        assert result == '営業部'

    def test_substring_match(self):
        """エッジケース: キー内に検索値が含まれる"""
        kintai_dict = {'営業部企画': 100}
        result = get_kintai_name(kintai_dict, '営業部')
        assert result == '営業部企画'

    def test_no_match(self):
        """エラーケース: マッチなし"""
        kintai_dict = {'営業部': 100}
        result = get_kintai_name(kintai_dict, '製造部')
        assert result is None

    def test_empty_dict(self):
        """エラーケース: 空の辞書"""
        kintai_dict = {}
        result = get_kintai_name(kintai_dict, '営業部')
        assert result is None

    def test_multiple_matches(self):
        """エッジケース: 複数候補がある場合"""
        kintai_dict = {'営業部': 100, '営業部A': 200}
        result = get_kintai_name(kintai_dict, '営業部')
        # 完全一致を優先
        assert result == '営業部'

class TestParseEnvFileActualHours:
    """allocate_actual_hours.py の parse_env_file() 関数のテスト"""

    def test_valid_env_file_with_standard_time(self, sample_env_file_actual_hours):
        """正常系: 標準時間有り"""
        results_dir, kintai_dir, master_dir, standard_time = parse_env_file(sample_env_file_actual_hours)
        assert os.path.exists(results_dir)
        assert os.path.exists(kintai_dir)
        assert os.path.exists(master_dir)
        assert standard_time == 8.0

    def test_valid_env_file_default_standard_time(self, sample_env_file_actual_hours_no_time):
        """正常系: 標準時間がデフォルト値"""
        results_dir, kintai_dir, master_dir, standard_time = parse_env_file(sample_env_file_actual_hours_no_time)
        assert standard_time == 7.5  # デフォルト値

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

class TestIntegrationActualHours:
    """allocate_actual_hours.py の統合テスト"""

    def test_kintai_name_lookup_flow(self):
        """正常系: 勤怠名前検索フロー"""
        kintai_dict = {
            '営業部': 1,
            '企画部': 2,
            '製造部': 3
        }

        test_cases = [
            ('営業部', '営業部'),
            ('企画部', '企画部'),
            ('営業部企画', '営業部'),  # 部分一致
            ('不明部門', None),  # マッチなし
        ]

        for input_name, expected in test_cases:
            result = get_kintai_name(kintai_dict, input_name)
            assert result == expected, f"get_kintai_name('{input_name}') should return {expected}, got {result}"
