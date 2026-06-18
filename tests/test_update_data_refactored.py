# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile
import csv
import pandas as pd

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from update_data import parse_env_file, load_and_merge, main

class TestParseEnvFileUpdateData:
    """update_data.py の parse_env_file() 関数のテスト"""

    def test_valid_env_file(self, sample_env_file_update_data):
        """正常系: 有効なenvファイル"""
        root_dir, list_dir, results_dir, test_dir = parse_env_file(sample_env_file_update_data)
        assert os.path.exists(root_dir)
        assert 'list' in list_dir
        assert 'results' in results_dir
        assert 'test' in test_dir

    def test_env_file_not_found(self):
        """エラーケース: ファイルが存在しない"""
        with pytest.raises(FileNotFoundError):
            parse_env_file('/nonexistent/path/env')

    def test_env_file_insufficient_lines(self):
        """エラーケース: 行数が不足"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.env') as f:
            f.write('line1\n')
            f.write('line2\n')
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                parse_env_file(temp_path)
        finally:
            os.unlink(temp_path)

class TestLoadAndMergeUpdateData:
    """update_data.py の load_and_merge() 関数のテスト"""

    def test_load_and_merge_single_file(self, temp_project_dir):
        """正常系: 単一ファイルのマージ"""
        results_dir = temp_project_dir['results_dir']

        # テストCSVを作成
        csv_path = os.path.join(results_dir, 'test_allocated_costs.csv')
        with open(csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード', 'コスト'])
            writer.writerow(['N', 'code1', '100'])
            writer.writerow(['G', 'code2', '200'])

        # hinku_listDataFrame作成
        hinku_data = {
            'naigaikubun': ['N', 'G'],
            'hinku': ['code1', 'code2'],
            'category': ['Category1', 'Category2']
        }
        df_hinku = pd.DataFrame(hinku_data)

        # テスト実行
        df_result = load_and_merge([csv_path], df_hinku)

        # 検証
        assert len(df_result) == 2
        assert 'category' in df_result.columns
        assert df_result.loc[0, 'category'] == 'Category1'

    def test_load_and_merge_multiple_files(self, temp_project_dir):
        """正常系: 複数ファイルの縦結合"""
        results_dir = temp_project_dir['results_dir']

        # 複数CSVを作成
        file_paths = []
        for month in ['202605', '202606']:
            csv_path = os.path.join(results_dir, f'{month}_allocated_hours.csv')
            with open(csv_path, 'w', encoding='cp932', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['内外製区分', '品区コード', '工数'])
                writer.writerow(['N', 'code1', '80'])
                writer.writerow(['G', 'code2', '160'])
            file_paths.append(csv_path)

        # hinku_listDataFrame作成
        hinku_data = {
            'naigaikubun': ['N', 'G'],
            'hinku': ['code1', 'code2'],
            'category': ['Cat1', 'Cat2']
        }
        df_hinku = pd.DataFrame(hinku_data)

        # テスト実行
        df_result = load_and_merge(file_paths, df_hinku)

        # 検証：4行（2月 × 2行）
        assert len(df_result) == 4
        assert 'category' in df_result.columns

    def test_load_and_merge_empty_files(self):
        """エッジケース: ファイルが空"""
        df_hinku = pd.DataFrame({'naigaikubun': [], 'hinku': []})

        df_result = load_and_merge([], df_hinku)

        assert df_result.empty

    def test_load_and_merge_left_join(self, temp_project_dir):
        """正常系: LEFT JOINでマスタ外の値も保持"""
        results_dir = temp_project_dir['results_dir']

        csv_path = os.path.join(results_dir, 'test_leftjoin.csv')
        with open(csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['内外製区分', '品区コード', 'データ'])
            writer.writerow(['N', 'code1', 'value1'])
            writer.writerow(['y', 'y2', 'value2'])

        # hinku_listは code1 と y1 のみ
        hinku_data = {
            'naigaikubun': ['N', 'y'],
            'hinku': ['code1', 'y1'],
            'category': ['Cat1', 'Cat2']
        }
        df_hinku = pd.DataFrame(hinku_data)

        df_result = load_and_merge([csv_path], df_hinku)

        assert len(df_result) == 2
        # y2はマスタにないため categoryはNaN
        assert pd.isna(df_result.loc[1, 'category'])

class TestMainUpdateData:
    """update_data.py の main() 関数のテスト"""

    def test_main_full_workflow(self, temp_project_dir):
        """正常系: 完全なメイン処理フロー"""
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']
        test_dir = os.path.join(temp_project_dir['root'], 'test')

        # hinku_list.csvを作成
        hinku_csv_path = os.path.join(list_dir, 'hinku_list.csv')
        with open(hinku_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['naigaikubun', 'hinku', 'category'])
            writer.writerow(['N', 'code1', 'Normal'])
            writer.writerow(['G', 'code2', 'External'])

        # 月次ファイルを作成
        for ftype_name, ftype_pattern in [('costs', 'allocated_costs'), ('hours', 'allocated_hours'), ('pm', 'person_months')]:
            csv_path = os.path.join(results_dir, f'202605_{ftype_pattern}.csv')
            with open(csv_path, 'w', encoding='cp932', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['内外製区分', '品区コード', 'amount'])
                writer.writerow(['N', 'code1', '100'])
                writer.writerow(['G', 'code2', '200'])

        # env ファイルを作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        # main() を実行
        df_costs, df_hours, df_pm = main(env_path)

        # 検証
        assert len(df_costs) == 2
        assert len(df_hours) == 2
        assert len(df_pm) == 2

        # JS出力ファイル確認
        js_path = os.path.join(test_dir, 'data.js')
        assert os.path.exists(js_path)

        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            assert 'const allCosts' in js_content
            assert 'const allHours' in js_content
            assert 'const allPersonMonths' in js_content

    def test_main_with_missing_hinku_list(self, temp_project_dir):
        """エラーケース: hinku_list.csvが見当たらない"""
        # env ファイルを作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        # hinku_list.csvは作成しない
        with pytest.raises(FileNotFoundError):
            main(env_path)

class TestIntegrationUpdateData:
    """update_data.py の統合テスト"""

    def test_full_data_pipeline(self, temp_project_dir):
        """正常系: 完全なデータパイプライン"""
        list_dir = temp_project_dir['list_dir']
        results_dir = temp_project_dir['results_dir']

        # hinku_list.csvを作成
        hinku_csv_path = os.path.join(list_dir, 'hinku_list.csv')
        with open(hinku_csv_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['naigaikubun', 'hinku', 'category'])
            writer.writerow(['N', 'code1', 'Normal'])
            writer.writerow(['G', 'code2', 'External'])
            writer.writerow(['y', 'y1', 'YearProduct'])

        # 複数月分のファイルを作成
        for month in ['202605', '202606', '202607']:
            for ftype_name, ftype_pattern in [('costs', 'allocated_costs'), ('hours', 'allocated_hours'), ('pm', 'person_months')]:
                csv_path = os.path.join(results_dir, f'{month}_{ftype_pattern}.csv')
                with open(csv_path, 'w', encoding='cp932', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['内外製区分', '品区コード', 'amount'])
                    writer.writerow(['N', 'code1', '100'])
                    writer.writerow(['G', 'code2', '200'])
                    writer.writerow(['y', 'y1', '150'])

        # env ファイルを作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('dummy2\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        # main() を実行
        df_costs, df_hours, df_pm = main(env_path)

        # 検証：3月 × 3行 = 9行
        assert len(df_costs) == 9
        assert len(df_hours) == 9
        assert len(df_pm) == 9
        assert 'category' in df_costs.columns
        assert 'category' in df_hours.columns
        assert 'category' in df_pm.columns
