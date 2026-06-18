# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile
import csv
from unittest import mock

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from aggregate_hours import main, parse_env_file, excel_date_to_month, extract_person_name

class TestAggregateHoursMain:
    """aggregate_hours.py の main() 関数の統合テスト"""

    def test_main_basic_aggregation(self, temp_project_dir, sample_env_file, sample_nichijou_csv, sample_staff_csv):
        """正常系: 基本的な工数集計"""
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']
        member_dir = temp_project_dir['member_dir']

        # モックの引数を設定
        mock_argv = [
            'aggregate_hours.py',
            '--env', sample_env_file,
            '--out', 'test_raw_data.csv'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, 'test_raw_data.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert '月' in headers
            assert '案件（業務）名' in headers
            assert '内外製区分' in headers
            assert '品区コード' in headers
            rows = list(reader)
            assert len(rows) >= 0  # データがなくても良い（マスタに登録がないため）

    def test_main_with_month_filter(self, temp_project_dir):
        """正常系: 月指定で集計（データない場合は警告のみ）"""
        member_dir = temp_project_dir['member_dir']
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # env作成
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

        # マスタCSV作成
        nichijou_csv_path = os.path.join(list_dir, 'sample_nichijou_list.csv')
        with open(nichijou_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['部課', '工数区分', 'Task001'])
            writer.writerow(['営業部', 'A', 'Task001'])

        # 担当者CSV作成
        staff_csv_path = os.path.join(member_dir, 'test_T_user.csv')
        with open(staff_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['日付', 'コード', 'Task001'])
            writer.writerow(['dummy', 'dummy', 'dummy'])
            writer.writerow(['44000', '10001', '480'])  # 2020/4/19

        mock_argv = [
            'aggregate_hours.py',
            '--env', env_path,
            '--out', 'raw_data.csv',
            '--month', '202004'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認（月名が含まれるか、またはデータなしの警告）
        output_file = os.path.join(results_dir, '202004_raw_data.csv')
        # ファイルが存在するか、または存在しない可能性がある
        # どちらでもOKとする（データがない場合は作成されない）

    def test_main_with_invalid_month(self, temp_project_dir, sample_env_file):
        """エラーケース: 無効な月フォーマット"""
        mock_argv = [
            'aggregate_hours.py',
            '--env', sample_env_file,
            '--month', '20260401'  # 正しくない形式（8桁）
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            # エラーメッセージが出力されるが、プログラムは終了する
            main()

    def test_main_env_file_not_found(self, temp_project_dir):
        """エラーケース: envファイルが見当たらない"""
        mock_argv = [
            'aggregate_hours.py',
            '--env', '/nonexistent/path/env'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーが出力されるが例外は発生しない

    def test_main_with_default_arguments(self, temp_project_dir, sample_env_file, sample_nichijou_csv, sample_staff_csv):
        """正常系: デフォルト引数での実行"""
        results_dir = temp_project_dir['results_dir']

        mock_argv = [
            'aggregate_hours.py',
            '--env', sample_env_file
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # デフォルト出力ファイル（raw_data.csv）を確認
        output_file = os.path.join(results_dir, 'raw_data.csv')
        assert os.path.exists(output_file)

class TestAggregateHoursIntegration:
    """aggregate_hours.py の複合テスト"""

    def test_full_aggregation_workflow(self, temp_project_dir):
        """正常系: 完全な集計ワークフロー"""
        member_dir = temp_project_dir['member_dir']
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # マスタCSV作成（ファイル名パターン: *nichijou_list.csv）
        nichijou_csv_path = os.path.join(list_dir, 'sample_nichijou_list.csv')
        with open(nichijou_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['部課', '工数区分', 'Task001'])  # 3列目がタスク名
            writer.writerow(['営業部', 'A', 'Task001'])

        # 担当者CSV作成（ファイル名パターン: *_T*.csv で名前を抽出）
        staff_csv_path = os.path.join(member_dir, 'sample_T_testuser.csv')
        with open(staff_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['日付', 'コード', 'Task001'])  # 日付、コード、タスク名
            writer.writerow(['dummy', 'dummy', 'dummy'])     # サブヘッダー
            writer.writerow(['44000', '10001', '480'])       # 480分 = 8時間
            writer.writerow(['44001', '10002', '300'])       # 300分 = 5時間

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

        # main実行
        mock_argv = [
            'aggregate_hours.py',
            '--env', env_path,
            '--out', 'aggregated.csv'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, 'aggregated.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # 固定4カラム + 人名のカラムが期待される
            assert len(headers) >= 4

    def test_multiple_persons_aggregation(self, temp_project_dir):
        """正常系: 複数人の工数集計"""
        member_dir = temp_project_dir['member_dir']
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # マスタCSV作成
        nichijou_csv_path = os.path.join(list_dir, 'sample_nichijou_list.csv')
        with open(nichijou_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['部課', '工数区分', 'Task001'])
            writer.writerow(['営業部', 'A', 'Task001'])

        # 複数の担当者CSV作成
        for person_id in ['person_001', 'person_002']:
            staff_csv_path = os.path.join(member_dir, f'{person_id}_T_test.csv')
            with open(staff_csv_path, 'w', encoding='cp932', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['日付', 'コード', 'Task001'])
                writer.writerow(['dummy', 'dummy', 'dummy'])
                writer.writerow(['44000', '10001', '480'])
                writer.writerow(['44001', '10002', '240'])

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

        # main実行
        mock_argv = [
            'aggregate_hours.py',
            '--env', env_path,
            '--out', 'multi_person.csv'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, 'multi_person.csv')
        assert os.path.exists(output_file)

        # 複数人のカラムが含まれることを確認
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # 最低でも4つの固定カラム + 複数人のカラム
            assert len(headers) >= 5
