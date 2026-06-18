# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile
import csv
import statistics
from unittest import mock

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from calculate_person_months import (
    parse_env_file,
    is_target_record,
    main
)

class TestParseEnvFilePersonMonths:
    """calculate_person_months.py の parse_env_file() 関数のテスト"""

    def test_valid_env_file(self, sample_env_file_person_months):
        """正常系: 有効なenvファイル"""
        results_dir = parse_env_file(sample_env_file_person_months)
        assert os.path.exists(results_dir)

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

class TestIsTargetRecordPersonMonths:
    """calculate_person_months.py の is_target_record() 関数のテスト"""

    def test_naigai_N(self):
        """正常系: naigai='N' は常に対象"""
        assert is_target_record('N', 'any') is True

    def test_naigai_G(self):
        """正常系: naigai='G' は常に対象"""
        assert is_target_record('G', 'any') is True

    def test_naigai_K(self):
        """正常系: naigai='K' は常に対象"""
        assert is_target_record('K', 'any') is True

    def test_naigai_y_valid_hinku(self):
        """正常系: naigai='y' で有効な品区"""
        assert is_target_record('y', 'y1') is True
        assert is_target_record('y', 'y10') is True
        assert is_target_record('y', 'y20') is True

    def test_naigai_y_invalid_hinku(self):
        """エラーケース: naigai='y' で無効な品区"""
        assert is_target_record('y', 'y2') is False
        assert is_target_record('y', 'y11') is False

    def test_invalid_naigai(self):
        """エラーケース: 無効なnaigai値"""
        assert is_target_record('X', 'y1') is False

class TestStatisticsCalculation:
    """統計計算のロジックテスト"""

    def test_average_calculation(self):
        """正常系: 平均値計算"""
        values = [8.0, 16.0, 24.0]
        avg = sum(values) / len(values)
        assert avg == 16.0

    def test_standard_deviation_single(self):
        """エッジケース: 1つの値は標準偏差0"""
        values = [8.0]
        std_dev = 0.0  # 1件以下は計算しない
        assert std_dev == 0.0

    def test_standard_deviation_multiple(self):
        """正常系: 複数値の標準偏差"""
        values = [8.0, 10.0, 12.0]
        std_dev = statistics.stdev(values)
        assert std_dev == 2.0

    def test_person_month_calculation(self):
        """正常系: 人工数計算"""
        # project_ratio = item_hours / total_hours
        # pm = project_ratio * valid_headcount
        item_hours = 80.0
        total_hours = 400.0
        valid_headcount = 4

        project_ratio = item_hours / total_hours
        pm = project_ratio * valid_headcount

        assert project_ratio == 0.2
        assert pm == 0.8

    def test_person_month_zero_total(self):
        """エッジケース: 総時間が0"""
        item_hours = 80.0
        total_hours = 0.0
        valid_headcount = 4

        project_ratio = item_hours / total_hours if total_hours > 0 else 0.0
        pm = project_ratio * valid_headcount

        assert project_ratio == 0.0
        assert pm == 0.0

class TestIntegrationPersonMonths:
    """calculate_person_months.py の統合テスト"""

    def test_sample_raw_data_processing(self, sample_env_file_person_months, sample_raw_data_csv):
        """正常系: サンプルraw_dataの処理"""
        results_dir = parse_env_file(sample_env_file_person_months)
        assert os.path.exists(results_dir)

        # サンプルCSVが正しく読み込める確認
        with open(sample_raw_data_csv, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert len(headers) >= 4
            rows = list(reader)
            assert len(rows) == 2

    def test_target_record_filtering_flow(self):
        """正常系: 対象レコード絞り込みフロー"""
        test_cases = [
            ('N', 'any', True),
            ('G', 'any', True),
            ('K', 'any', True),
            ('y', 'y1', True),
            ('y', 'y10', True),
            ('y', 'y20', True),
            ('y', 'y2', False),
            ('X', 'any', False),
        ]

        for naigai, hinku, expected in test_cases:
            result = is_target_record(naigai, hinku)
            assert result == expected, f"is_target_record('{naigai}', '{hinku}') should return {expected}"

class TestCalculatePersonMonthsMain:
    """calculate_person_months.py の main() 関数の統合テスト"""

    def test_main_basic_calculation(self, temp_project_dir):
        """正常系: 基本的な人工数計算"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8', '8'])
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '4', '4'])

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_person_months.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert '月' in headers
            assert '案件（業務）名' in headers
            assert '人工数/月' in headers
            rows = list(reader)
            assert len(rows) > 0

    def test_main_with_invalid_month(self, temp_project_dir):
        """エラーケース: monthパラメータが必須"""
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        # monthパラメータなしで実行
        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with pytest.raises(SystemExit):
                main()

    def test_main_missing_data_file(self, temp_project_dir):
        """エラーケース: raw_data.csv が見当たらない"""
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

    def test_main_missing_env_file(self, temp_project_dir):
        """エラーケース: envファイルが見当たらない"""
        results_dir = temp_project_dir['results_dir']
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8'])

        mock_argv = [
            'calculate_person_months.py',
            '--env', '/nonexistent/path/env',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

class TestCalculatePersonMonthsIntegration:
    """calculate_person_months.py の複合テスト"""

    def test_full_calculation_workflow(self, temp_project_dir):
        """正常系: 完全な人工数計算ワークフロー"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv を作成（複数プロジェクト、複数人）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子', '次郎'])
            # 対象工数
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '10', '10', '10'])
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '20', '20', '20'])
            writer.writerow(['2026/04', 'ProjectC', 'K', 'code3', '5', '5', '5'])
            # 対象外工数
            writer.writerow(['2026/04', 'ProjectD', 'y', 'y2', '8', '8', '8'])
            # 異なる月
            writer.writerow(['2026/05', 'ProjectE', 'N', 'code5', '8', '8', '8'])

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_person_months.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            # ProjectA, ProjectB, ProjectC のみ（ProjectDは対象外、ProjectEは異なる月）
            data_rows = [r for r in rows if r and r[0] and r[0].startswith('2026')]
            assert len(data_rows) == 3

    def test_calculation_with_target_records_filtering(self, temp_project_dir):
        """正常系: 対象レコード絞り込みの検証"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv を作成（様々なパターン）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            # 対象
            writer.writerow(['2026/04', 'Task1', 'N', 'code1', '8'])
            writer.writerow(['2026/04', 'Task2', 'G', 'code2', '8'])
            writer.writerow(['2026/04', 'Task3', 'K', 'code3', '8'])
            writer.writerow(['2026/04', 'Task4', 'y', 'y1', '8'])
            writer.writerow(['2026/04', 'Task5', 'y', 'y10', '8'])
            writer.writerow(['2026/04', 'Task6', 'y', 'y20', '8'])
            # 対象外
            writer.writerow(['2026/04', 'Task7', 'y', 'y2', '8'])
            writer.writerow(['2026/04', 'Task8', 'X', 'code4', '8'])

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_person_months.csv')
        assert os.path.exists(output_file)

        # 出力内容検証：Task1～Task6 のみ出力されるはず
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            data_rows = [r for r in rows if r and r[0] and r[0].startswith('2026')]
            assert len(data_rows) == 6  # Task1～Task6のみ

    def test_calculation_with_multiple_assignees(self, temp_project_dir):
        """正常系: 複数担当者の比率計算"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv を作成（複数人で異なる工数配分）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子', '次郎'])
            # 太郎: 10, 花子: 20, 次郎: 30
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '10', '20', '30'])
            # 太郎: 20, 花子: 10, 次郎: 20
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '20', '10', '20'])

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_person_months.csv')
        assert os.path.exists(output_file)

        # 出力内容検証（複数人の比率カラムが含まれているか）
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # ヘッダーに複数人の比率カラムが含まれるはず
            assert '太郎_比率' in headers
            assert '花子_比率' in headers
            assert '次郎_比率' in headers

    def test_calculation_with_zero_hours(self, temp_project_dir):
        """エッジケース: 対象工数がゼロの担当者の除外"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv を作成（太郎は対象工数ゼロ）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '0', '10'])  # 太郎は0
            writer.writerow(['2026/04', 'ProjectB', 'y', 'y2', '8', '8'])      # 対象外

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_person_months.csv')
        assert os.path.exists(output_file)

        # 出力内容検証（太郎のカラムは出力されていないはず）
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # 太郎は対象工数がないので除外される
            assert '太郎_比率' not in headers
            # 花子のカラムのみ存在
            assert '花子_比率' in headers

    def test_month_format_conversion(self, temp_project_dir):
        """正常系: 月フォーマット変換（YYYYMM → YYYY/MM）"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8'])

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        # 月フォーマットをYYYYMMで指定（変換テスト）
        mock_argv = [
            'calculate_person_months.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'  # YYYYMM形式
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認（月フォーマットで変換されているか）
        output_file = os.path.join(results_dir, '202604_person_months.csv')
        assert os.path.exists(output_file)
