# -*- coding: utf-8 -*-
import pytest
import os
import sys
import csv
import tempfile
from unittest import mock

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from allocate_actual_hours import main, parse_env_file, get_kintai_name, parse_kintai_html

class TestParseEnvFileActualHours:
    """allocate_actual_hours.py の parse_env_file() 関数のテスト"""

    def test_valid_env_file(self, sample_env_file_actual_hours):
        """正常系: 有効なenvファイル"""
        results_dir, kintai_dir, master_dir, standard_time = parse_env_file(sample_env_file_actual_hours)
        assert os.path.exists(results_dir)
        assert 'kintai' in kintai_dir
        assert os.path.exists(master_dir)
        assert standard_time == 8.0

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

    def test_invalid_standard_time_defaults(self, temp_project_dir):
        """エラーケース: 無効な標準時間はデフォルト値に"""
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('invalid_value\n')

        results_dir, kintai_dir_out, master_dir, standard_time = parse_env_file(env_path)
        assert standard_time == 7.5  # デフォルト値

class TestGetKintaiName:
    """allocate_actual_hours.py の get_kintai_name() 関数のテスト"""

    def test_exact_match(self):
        """正常系: 完全一致"""
        kintai_dict = {'太郎': 8.0, '花子': 7.5}
        result = get_kintai_name(kintai_dict, '太郎')
        assert result == '太郎'

    def test_match_with_space_removal(self):
        """正常系: スペース除去後の一致"""
        kintai_dict = {'太郎': 8.0}
        result = get_kintai_name(kintai_dict, '太　郎')  # 全角スペース
        assert result == '太郎'

    def test_partial_match(self):
        """正常系: 部分一致"""
        kintai_dict = {'太郎': 8.0}
        result = get_kintai_name(kintai_dict, '太郎（営業部）')
        assert result == '太郎'

    def test_no_match(self):
        """エラーケース: 一致なし"""
        kintai_dict = {'太郎': 8.0}
        result = get_kintai_name(kintai_dict, '次郎')
        assert result is None

class TestParseKintaiHtml:
    """allocate_actual_hours.py の parse_kintai_html() 関数のテスト"""

    def test_parse_simple_html(self, temp_project_dir):
        """正常系: シンプルなHTML解析"""
        html_path = os.path.join(temp_project_dir['root'], 'test_kintai.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('''<html>
<body>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>正社員</td><td>8.0</td></tr>
<tr><td>花子</td><td>契約社員</td><td>7.5</td></tr>
</table>
</body>
</html>''')

        work_hours, leaves = parse_kintai_html(html_path)
        assert '太郎' in work_hours
        assert work_hours['太郎'] == 8.0
        assert '花子' in work_hours
        assert work_hours['花子'] == 7.5

    def test_parse_html_with_leave_columns(self, temp_project_dir):
        """正常系: 休暇カラム付きHTML"""
        html_path = os.path.join(temp_project_dir['root'], 'test_kintai_leaves.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('''<html>
<body>
<table>
<tr><th>名前</th><th>実働時間</th><th>有休</th><th>欠勤</th></tr>
<tr><td>太郎</td><td>8.0</td><td>0.5</td><td>0</td></tr>
<tr><td>花子</td><td>7.5</td><td>1.0</td><td>0.5</td></tr>
</table>
</body>
</html>''')

        work_hours, leaves = parse_kintai_html(html_path)
        assert leaves['太郎']['有休'] == 0.5
        assert leaves['太郎']['欠勤'] == 0.0
        assert leaves['花子']['有休'] == 1.0
        assert leaves['花子']['欠勤'] == 0.5

    def test_parse_html_with_name_cleanup(self, temp_project_dir):
        """正常系: 名前のクリーンアップ（番号・スペース除去）"""
        html_path = os.path.join(temp_project_dir['root'], 'test_kintai_cleanup.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('''<html>
<body>
<table>
<tr><th>名前</th><th>実働時間</th></tr>
<tr><td>001太郎</td><td>8.0</td></tr>
<tr><td>太　郎</td><td>8.0</td></tr>
</table>
</body>
</html>''')

        work_hours, leaves = parse_kintai_html(html_path)
        # 001は除去される、スペースも除去される
        assert '太郎' in work_hours

class TestAllocateActualHoursMain:
    """allocate_actual_hours.py の main() 関数の統合テスト"""

    def test_main_basic_allocation(self, temp_project_dir):
        """正常系: 基本的な実労働時間按分"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

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
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # nichijou_list.csv作成（189期マスタ）
        master_csv = os.path.join(temp_project_dir['list_dir'], '189_nichijou_list.csv')
        with open(master_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['部課', '工数区分', 'タスク名'])
            writer.writerow(['営業部', 'A', '休暇'])

        # ダミー勤怠HTMLファイル作成
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>8.0</td></tr>
<tr><td>花子</td><td>7.5</td></tr>
</table>
</html>''')

        # get_soneki_costs をモック
        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_allocated_hours.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert '月' in headers
            assert '案件（業務）名' in headers
            assert '合計時間(h)' in headers
            rows = list(reader)
            assert len(rows) > 0

    def test_main_with_invalid_month(self, temp_project_dir):
        """エラーケース: monthパラメータが必須"""
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # monthパラメータなしで実行
        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with pytest.raises(SystemExit):
                main()

    def test_main_missing_kintai_file(self, temp_project_dir):
        """エラーケース: 勤怠ファイルが見当たらない"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
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
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # 勤怠ファイルは作成しない
        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

    def test_main_missing_data_file(self, temp_project_dir):
        """エラーケース: raw_data.csv が見当たらない"""
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # 勤怠ファイルのみ作成（raw_data.csvは作成しない）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('<table><tr><th>名前</th><th>実働時間</th></tr></table>')

        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

class TestAllocateActualHoursIntegration:
    """allocate_actual_hours.py の複合テスト"""

    def test_full_allocation_workflow(self, temp_project_dir):
        """正常系: 完全な実労働時間按分ワークフロー"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        master_dir = temp_project_dir['list_dir']
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成（複数プロジェクト）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子', '次郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '10', '10', '10'])  # 合計30h
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '20', '20', '20'])  # 合計60h

        # envファイル作成
        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # 勤怠HTMLファイル作成（全員のデータ）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>8.0</td></tr>
<tr><td>花子</td><td>7.5</td></tr>
<tr><td>次郎</td><td>8.0</td></tr>
</table>
</html>''')

        # nichijou_list.csv作成（休暇マスタ）
        master_csv = os.path.join(master_dir, '189_nichijou_list.csv')
        with open(master_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['部課', '工数区分', 'タスク名'])
            writer.writerow(['営業部', 'A', '休暇'])

        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_allocated_hours.csv')
        assert os.path.exists(output_file)

        # 出力内容検証
        with open(output_file, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

            # データ行の確認（2プロジェクト）
            data_rows = [r for r in rows if r and r[0] and r[0].startswith('2026')]
            assert len(data_rows) == 2

    def test_allocation_with_no_matching_assignees(self, temp_project_dir):
        """エラーケース: 勤怠データと一致する担当者がいない"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8', '8'])

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # 勤怠HTMLファイル作成（異なる名前）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>実働時間</th></tr>
<tr><td>次郎</td><td>8.0</td></tr>
<tr><td>三郎</td><td>7.5</td></tr>
</table>
</html>''')

        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()  # エラーメッセージが出力される

    def test_allocation_with_leave_data(self, temp_project_dir):
        """正常系: 休暇・欠勤データ付きの按分"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        master_dir = temp_project_dir['list_dir']
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '16'])

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('8.0\n')

        # 勤怠HTMLファイル作成（休暇データ付き）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>実働時間</th><th>有休</th><th>欠勤</th></tr>
<tr><td>太郎</td><td>8.0</td><td>2.0</td><td>1.0</td></tr>
</table>
</html>''')

        # nichijou_list.csv作成（休暇マスタ）
        master_csv = os.path.join(master_dir, '189_nichijou_list.csv')
        with open(master_csv, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['部課', '工数区分', 'タスク名'])
            writer.writerow(['営業部', 'A', '休暇'])

        mock_argv = [
            'allocate_actual_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            main()

        # 出力ファイル確認
        output_file = os.path.join(results_dir, '202604_allocated_hours.csv')
        assert os.path.exists(output_file)

        # 出力内容検証（休暇換算セクションが含まれるか）
        with open(output_file, 'r', encoding='cp932') as f:
            content = f.read()
            assert '[休暇・欠勤等換算]' in content
