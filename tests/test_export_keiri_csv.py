# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile
import csv
from unittest import mock

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from export_keiri_csv import (
    parse_env_file,
    is_target_record,
    main
)

class TestParseEnvFileExportKeiri:
    """export_keiri_csv.py の parse_env_file() 関数のテスト"""

    def test_valid_env_file(self, sample_env_file_export_keiri):
        """正常系: 有効なenvファイル"""
        results_dir, master_dir = parse_env_file(sample_env_file_export_keiri)
        assert os.path.exists(results_dir)
        assert os.path.exists(master_dir)

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

class TestIsTargetRecordExportKeiri:
    """export_keiri_csv.py の is_target_record() 関数のテスト"""

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
        assert is_target_record('y', 'y21') is False

    def test_naigai_Y_uppercase(self):
        """エッジケース: naigai='Y' (大文字)"""
        assert is_target_record('Y', 'y1') is True
        assert is_target_record('Y', 'y2') is False

    def test_invalid_naigai(self):
        """エラーケース: 無効なnaigai値"""
        assert is_target_record('X', 'y1') is False
        assert is_target_record('', 'y1') is False

    def test_whitespace_handling(self):
        """エッジケース: ホワイトスペース処理"""
        assert is_target_record(' N ', 'any') is True
        assert is_target_record('  y  ', ' y1 ') is True
        assert is_target_record(' y ', ' y2 ') is False

class TestHinkuListProcessing:
    """hinku_list.csvの処理テスト"""

    def test_hinku_list_parsing(self, sample_hinku_list_csv):
        """正常系: hinku_list.csvの解析"""
        with open(sample_hinku_list_csv, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert len(headers) >= 2
            rows = list(reader)
            assert len(rows) == 3

    def test_target_record_filtering_from_hinku(self, sample_hinku_list_csv):
        """正常系: hinku_listから対象レコードの抽出"""
        target_records = []
        with open(sample_hinku_list_csv, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダースキップ
            for row in reader:
                if len(row) >= 2:
                    k = row[0].strip()
                    h = row[1].strip()
                    if is_target_record(k, h):
                        target_records.append((k, h))

        # サンプルデータでは2件が対象
        assert len(target_records) == 2
        assert ('N', 'code1') in target_records
        assert ('G', 'code2') in target_records

class TestIntegrationExportKeiri:
    """export_keiri_csv.py の統合テスト"""

    def test_full_export_flow(self, sample_env_file_export_keiri, sample_hinku_list_csv):
        """正常系: 全フロー"""
        results_dir, master_dir = parse_env_file(sample_env_file_export_keiri)
        assert os.path.exists(results_dir)
        assert os.path.exists(master_dir)

        # hinku_listが読み込める確認
        assert os.path.exists(sample_hinku_list_csv)

    def test_month_format_normalization(self):
        """正常系: 月フォーマット正規化"""
        test_cases = [
            ('202603', '2026/03'),
            ('2026-03', '2026/03'),
            ('2026/03', '2026/03'),
        ]

        for input_month, expected_output in test_cases:
            target_month = input_month.replace('-', '/')
            if len(target_month) == 6 and target_month.isdigit():
                target_month = f"{target_month[:4]}/{target_month[4:]}"
            assert target_month == expected_output

class TestExportKeiricsvMain:
    """export_keiri_csv.py の main() 関数の統合テスト"""

    def test_main_basic_export(self, temp_project_dir):
        """正常系: 基本的な経理データエクスポート"""
        results_dir = temp_project_dir['results_dir']
        master_dir = temp_project_dir['list_dir']

        # hinku_list.csv を作成
        hinku_csv = os.path.join(master_dir, '189_hinku_list.csv')
        with open(hinku_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード'])
            writer.writerow(['N', 'code1'])
            writer.writerow(['G', 'code2'])

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_keiri_ratio.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert '内外製区分' in headers
            assert '品区コード' in headers
            assert '工数(hour)' in headers
            assert '比率' in headers
            rows = list(reader)
            assert len(rows) == 2  # N code1, G code2

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

        mock_argv = [
            'export_keiri_csv.py',
            '--env', env_path
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with pytest.raises(SystemExit):
                main()

    def test_main_missing_hinku_list(self, temp_project_dir):
        """エラーケース: hinku_list.csv が見当たらない"""
        results_dir = temp_project_dir['results_dir']

        # raw_data.csv のみ作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8'])

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

    def test_main_missing_data_file(self, temp_project_dir):
        """エラーケース: raw_data.csv が見当たらない"""
        master_dir = temp_project_dir['list_dir']

        # hinku_list.csv のみ作成
        hinku_csv = os.path.join(master_dir, '189_hinku_list.csv')
        with open(hinku_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード'])
            writer.writerow(['N', 'code1'])

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

    def test_main_zero_target_hours(self, temp_project_dir):
        """警告ケース: 対象工数がゼロ"""
        results_dir = temp_project_dir['results_dir']
        master_dir = temp_project_dir['list_dir']

        # hinku_list.csv を作成
        hinku_csv = os.path.join(master_dir, '189_hinku_list.csv')
        with open(hinku_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード'])
            writer.writerow(['N', 'code1'])

        # raw_data.csv（対象月にデータがない）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/05', 'ProjectA', 'N', 'code1', '8'])  # 異なる月

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイルは作成されるはず（警告のみ）
        output_file = os.path.join(results_dir, '202604_keiri_ratio.csv')
        assert os.path.exists(output_file)

class TestExportKeiricsvIntegration:
    """export_keiri_csv.py の複合テスト"""

    def test_full_export_with_multiple_records(self, temp_project_dir):
        """正常系: 複数レコードのエクスポート"""
        results_dir = temp_project_dir['results_dir']
        master_dir = temp_project_dir['list_dir']

        # hinku_list.csv を作成（複数レコード）
        hinku_csv = os.path.join(master_dir, '189_hinku_list.csv')
        with open(hinku_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード'])
            writer.writerow(['N', 'code1'])
            writer.writerow(['G', 'code2'])
            writer.writerow(['K', 'code3'])
            writer.writerow(['y', 'y1'])

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子', '次郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '10', '20', '30'])
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '5', '5', '5'])
            writer.writerow(['2026/04', 'ProjectC', 'K', 'code3', '3', '3', '3'])
            writer.writerow(['2026/04', 'ProjectD', 'y', 'y1', '2', '2', '2'])
            # 対象外
            writer.writerow(['2026/04', 'ProjectE', 'y', 'y2', '8', '8', '8'])
            # 異なる月
            writer.writerow(['2026/05', 'ProjectF', 'N', 'code1', '8', '8', '8'])

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_keiri_ratio.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
            # N, G, K, y1 の4行が出力されるはず
            assert len(rows) == 4

    def test_export_with_ratio_calculation(self, temp_project_dir):
        """正常系: 比率の計算検証"""
        results_dir = temp_project_dir['results_dir']
        master_dir = temp_project_dir['list_dir']

        # hinku_list.csv を作成
        hinku_csv = os.path.join(master_dir, '189_hinku_list.csv')
        with open(hinku_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード'])
            writer.writerow(['N', 'code1'])
            writer.writerow(['G', 'code2'])

        # raw_data.csv（100h + 50h = 150h）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '工数'])
            writer.writerow(['2026/04', 'TaskA', 'N', 'code1', '100'])
            writer.writerow(['2026/04', 'TaskB', 'G', 'code2', '50'])

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認と比率検証
        output_file = os.path.join(results_dir, '202604_keiri_ratio.csv')
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            # N: 100/150 = 0.666667
            # G: 50/150 = 0.333333
            assert float(rows[0][3]) == pytest.approx(0.666667, abs=0.000001)
            assert float(rows[1][3]) == pytest.approx(0.333333, abs=0.000001)

    def test_export_preserves_hinku_order(self, temp_project_dir):
        """正常系: hinku_listの順序を保持"""
        results_dir = temp_project_dir['results_dir']
        master_dir = temp_project_dir['list_dir']

        # hinku_list.csv を作成（特定の順序で）
        hinku_csv = os.path.join(master_dir, '189_hinku_list.csv')
        with open(hinku_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード'])
            writer.writerow(['K', 'code3'])  # 最初
            writer.writerow(['N', 'code1'])  # 次
            writer.writerow(['G', 'code2'])  # 最後

        # raw_data.csv
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '工数'])
            writer.writerow(['2026/04', 'TaskA', 'N', 'code1', '10'])
            writer.writerow(['2026/04', 'TaskB', 'G', 'code2', '20'])
            writer.writerow(['2026/04', 'TaskC', 'K', 'code3', '30'])

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
            'export_keiri_csv.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイルの順序確認
        output_file = os.path.join(results_dir, '202604_keiri_ratio.csv')
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            # hinku_listの順序を保持
            assert rows[0][0] == 'K'
            assert rows[0][1] == 'code3'
            assert rows[1][0] == 'N'
            assert rows[1][1] == 'code1'
            assert rows[2][0] == 'G'
            assert rows[2][1] == 'code2'
