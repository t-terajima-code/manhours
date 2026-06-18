# -*- coding: utf-8 -*-
import pytest
import os
import sys
import csv
import tempfile
from unittest import mock

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from allocate_costs import main, parse_env_file, is_target_record

class TestAllocateCostsMain:
    """allocate_costs.py の main() 関数の統合テスト"""

    def test_main_basic_allocation(self, temp_project_dir):
        """正常系: 基本的なコスト按分"""
        results_dir = temp_project_dir['results_dir']
        soneki_dir = os.path.join(temp_project_dir['root'], 'soneki')
        os.makedirs(soneki_dir, exist_ok=True)

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
            f.write('soneki\n')
            f.write('results\n')
            f.write('dummy4\n')

        # ダミーExcelファイルの名前を作成（実際の読み込みはモック）
        xlsx_path = os.path.join(soneki_dir, 'test_soneki_189.xlsx')
        with open(xlsx_path, 'w') as f:
            f.write('dummy')

        # get_soneki_costs をモック
        mock_argv = [
            'allocate_costs.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('allocate_costs.get_soneki_costs') as mock_soneki:
                mock_soneki.return_value = (10000.0, 2000.0)
                main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_allocated_costs.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert '月' in headers
            assert '按分比率' in headers
            assert '投入人員(人)' in headers
            rows = list(reader)
            assert len(rows) > 0

    def test_main_with_invalid_month(self, temp_project_dir):
        """エラーケース: 月パラメータが必須"""
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('soneki\n')
            f.write('results\n')
            f.write('dummy4\n')

        # monthパラメータなしで実行
        mock_argv = [
            'allocate_costs.py',
            '--env', env_path
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            # argparse がエラーを出力するため、例外が発生する
            with pytest.raises(SystemExit):
                main()

    def test_main_missing_data_file(self, temp_project_dir):
        """エラーケース: 入力データファイルが見当たらない"""
        soneki_dir = os.path.join(temp_project_dir['root'], 'soneki')
        os.makedirs(soneki_dir, exist_ok=True)

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('soneki\n')
            f.write('results\n')
            f.write('dummy4\n')

        # raw_data.csv は作成しない
        mock_argv = [
            'allocate_costs.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

class TestAllocateCostsIntegration:
    """allocate_costs.py の複合テスト"""

    def test_full_allocation_workflow(self, temp_project_dir):
        """正常系: 完全なコスト按分ワークフロー"""
        results_dir = temp_project_dir['results_dir']
        soneki_dir = os.path.join(temp_project_dir['root'], 'soneki')
        os.makedirs(soneki_dir, exist_ok=True)

        # raw_data.csv を作成（複数プロジェクト）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子', '次郎'])
            # 対象工数
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '10', '10', '10'])  # 合計30h
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '20', '20', '20'])  # 合計60h
            # 対象外工数
            writer.writerow(['2026/04', 'ProjectC', 'y', 'y2', '5', '5', '5'])       # y2は対象外
            writer.writerow(['2026/05', 'ProjectA', 'N', 'code1', '8', '8', '8'])    # 違う月なので対象外

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('soneki\n')
            f.write('results\n')
            f.write('dummy4\n')

        # ダミーExcelファイル作成
        xlsx_path = os.path.join(soneki_dir, 'soneki_189.xlsx')
        with open(xlsx_path, 'w') as f:
            f.write('dummy')

        mock_argv = [
            'allocate_costs.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('allocate_costs.get_soneki_costs') as mock_soneki:
                mock_soneki.return_value = (50000.0, 10000.0)  # 労務費50M千円、経費10M千円
                main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_allocated_costs.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            # ProjectA と ProjectB のみ出力されるはず（y2は対象外）
            data_rows = [r for r in rows if r and r[0] and r[0].startswith('2026')]
            assert len(data_rows) == 2

            # 合計行の検証
            total_row = [r for r in rows if r and r[0] == '[合計]']
            assert len(total_row) == 1
            # 合計時間 = 30 + 60 = 90
            assert float(total_row[0][4]) == pytest.approx(90.0, rel=1e-2)

    def test_target_record_filtering(self, temp_project_dir):
        """正常系: 対象レコードの絞り込み"""
        results_dir = temp_project_dir['results_dir']
        soneki_dir = os.path.join(temp_project_dir['root'], 'soneki')
        os.makedirs(soneki_dir, exist_ok=True)

        # raw_data.csv を作成（様々なパターン）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            # 対象（N, G, K, y1/y10/y20）
            writer.writerow(['2026/04', 'Task1', 'N', 'code1', '8'])
            writer.writerow(['2026/04', 'Task2', 'G', 'code2', '8'])
            writer.writerow(['2026/04', 'Task3', 'K', 'code3', '8'])
            writer.writerow(['2026/04', 'Task4', 'y', 'y1', '8'])
            writer.writerow(['2026/04', 'Task5', 'y', 'y10', '8'])
            writer.writerow(['2026/04', 'Task6', 'y', 'y20', '8'])
            # 対象外（y以外の値）
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
            f.write('soneki\n')
            f.write('results\n')
            f.write('dummy4\n')

        # ダミーExcelファイル作成
        xlsx_path = os.path.join(soneki_dir, 'soneki_189.xlsx')
        with open(xlsx_path, 'w') as f:
            f.write('dummy')

        mock_argv = [
            'allocate_costs.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('allocate_costs.get_soneki_costs') as mock_soneki:
                mock_soneki.return_value = (30000.0, 5000.0)
                main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_allocated_costs.csv')
        assert os.path.exists(output_file)

        # 出力内容検証：Task1～Task6 のみ出力されるはず（Task7, Task8は対象外）
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            data_rows = [r for r in rows if r and r[0] and r[0].startswith('2026')]
            assert len(data_rows) == 6  # Task1～Task6のみ
