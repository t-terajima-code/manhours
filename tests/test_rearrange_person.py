# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile
import csv

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from rearrange_person import rearrange_person

class TestRearrangePerson:
    """rearrange_person.py の rearrange_person() 関数のテスト"""

    def test_valid_rearrange_person_basic(self, temp_project_dir):
        """正常系: 基本的なデータ再配置"""
        # テスト用ディレクトリ構造
        member_dir = temp_project_dir['member_dir']
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # 日付CSVを作成
        date_csv_path = os.path.join(list_dir, '202605date.csv')
        with open(date_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'holiday'])
            writer.writerow(['20260501', '0'])
            writer.writerow(['20260502', '0'])

        # メンバーログCSVを作成
        member_csv_path = os.path.join(member_dir, 'member_log.csv')
        with open(member_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'person'])  # ヘッダー行
            writer.writerow(['day1', 'day2'])     # サブヘッダー行
            writer.writerow(['20260501', '8'])
            writer.writerow(['20260502', '8'])

        # 関数実行
        rearrange_person(
            path=temp_project_dir['root'],
            dir1='member',
            memberlog='log',
            dir2='results',
            outfile='output',
            list_dir='list',
            period='202605',
            dmax='20260510',
            dmin='20260401'
        )

        # 出力ファイル確認
        output_csv_path = os.path.join(results_dir, 'output.csv')
        assert os.path.exists(output_csv_path)

        # 出力データの検証
        with open(output_csv_path, 'r', encoding='cp932') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) >= 1
            assert 'date' in rows[0]

    def test_rearrange_person_missing_date_csv(self, temp_project_dir):
        """エラーケース: 日付CSVが見当たらない"""
        member_dir = temp_project_dir['member_dir']

        # メンバーログCSVのみ作成（日付CSVなし）
        member_csv_path = os.path.join(member_dir, 'member_log.csv')
        with open(member_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'person'])
            writer.writerow(['day1', 'day2'])
            writer.writerow(['20260501', '8'])

        # FileNotFoundError が発生することを確認
        with pytest.raises(FileNotFoundError):
            rearrange_person(
                path=temp_project_dir['root'],
                dir1='member',
                memberlog='log',
                dir2='results',
                outfile='output',
                list_dir='list',
                period='202605',
                dmax='20260510',
                dmin='20260401'
            )

    def test_rearrange_person_empty_members(self, temp_project_dir):
        """エッジケース: メンバーログファイルが空"""
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # 日付CSVを作成
        date_csv_path = os.path.join(list_dir, '202605date.csv')
        with open(date_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'holiday'])

        # メンバーログCSVは作成しない

        # 関数実行（ファイル自体がないため、ログはスキップされる）
        rearrange_person(
            path=temp_project_dir['root'],
            dir1='member',
            memberlog='nonexistent_log',
            dir2='results',
            outfile='output',
            list_dir='list',
            period='202605',
            dmax='20260510',
            dmin='20260401'
        )

        # 出力ファイル確認
        output_csv_path = os.path.join(results_dir, 'output.csv')
        assert os.path.exists(output_csv_path)

    def test_rearrange_person_with_incident_headers(self, temp_project_dir):
        """正常系: インシデントヘッダーあり"""
        list_dir = temp_project_dir['list_dir']
        member_dir = temp_project_dir['member_dir']
        results_dir = temp_project_dir['results_dir']

        # inc_header_list.txt を作成
        inc_header_path = os.path.join(list_dir, 'inc_header_list.txt')
        with open(inc_header_path, 'w', encoding='cp932') as f:
            f.write('incident1\n')
            f.write('incident2\n')

        # 日付CSVを作成
        date_csv_path = os.path.join(list_dir, '202605date.csv')
        with open(date_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'holiday'])
            writer.writerow(['20260501', '0'])

        # メンバーログCSVを作成
        member_csv_path = os.path.join(member_dir, 'member_log.csv')
        with open(member_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'person', 'incident1', 'incident2'])
            writer.writerow(['day1', 'day2', 'subheader1', 'subheader2'])
            writer.writerow(['20260501', '8', '1', '2'])

        # 関数実行
        rearrange_person(
            path=temp_project_dir['root'],
            dir1='member',
            memberlog='log',
            dir2='results',
            outfile='output',
            list_dir='list',
            period='202605',
            dmax='20260510',
            dmin='20260401'
        )

        # 出力ファイル確認
        output_csv_path = os.path.join(results_dir, 'output.csv')
        assert os.path.exists(output_csv_path)

class TestIntegrationRearrangePerson:
    """rearrange_person.py の統合テスト"""

    def test_rearrange_person_full_workflow(self, temp_project_dir):
        """正常系: 完全なワークフロー"""
        member_dir = temp_project_dir['member_dir']
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # 日付CSVを作成
        date_csv_path = os.path.join(list_dir, '202605date.csv')
        with open(date_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'holiday'])
            writer.writerow(['20260501', '0'])
            writer.writerow(['20260502', '0'])
            writer.writerow(['20260503', '0'])

        # メンバーログCSVを作成（複数メンバー）
        for member_id in ['001', '002']:
            member_csv_path = os.path.join(member_dir, f'member_{member_id}_log.csv')
            with open(member_csv_path, 'w', encoding='cp932', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'person', 'task1', 'task2'])
                writer.writerow(['day1', 'day2', 'subheader1', 'subheader2'])
                writer.writerow(['20260501', '8', '4', '4'])
                writer.writerow(['20260502', '8', '3', '5'])
                writer.writerow(['20260503', '8', '4', '4'])

        # 関数実行
        rearrange_person(
            path=temp_project_dir['root'],
            dir1='member',
            memberlog='log',
            dir2='results',
            outfile='merged_output',
            list_dir='list',
            period='202605',
            dmax='20260510',
            dmin='20260401'
        )

        # 出力ファイル確認
        output_csv_path = os.path.join(results_dir, 'merged_output.csv')
        assert os.path.exists(output_csv_path)

        # 出力ファイルのデータ検証
        with open(output_csv_path, 'r', encoding='cp932') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            # date, holiday, task1, task2 などのカラムが存在することを確認
            assert 'date' in rows[0]
            assert len(rows) > 0
