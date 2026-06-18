# -*- coding: utf-8 -*-
import pytest
import os
import sys
import tempfile
import csv
from unittest import mock

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from verify_hours import (
    parse_env_file,
    parse_kintai_html,
    main
)

class TestParseEnvFileVerifyHours:
    """verify_hours.py の parse_env_file() 関数のテスト"""

    def test_valid_env_file(self, sample_env_file_verify_hours):
        """正常系: 有効なenvファイル"""
        root_dir, results_dir, kintai_dir = parse_env_file(sample_env_file_verify_hours)
        assert os.path.exists(root_dir)
        assert os.path.exists(results_dir)
        assert os.path.exists(kintai_dir)

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

class TestParseKintaiHtml:
    """parse_kintai_html() 関数のテスト"""

    def test_parse_simple_html(self, sample_kintai_html):
        """正常系: シンプルなHTMLテーブル"""
        result = parse_kintai_html(sample_kintai_html)
        assert '太郎' in result
        assert result['太郎']['hours'] == 8.0
        assert result['太郎']['type'] == '正社員'

    def test_parse_html_with_leading_numbers(self, sample_kintai_html_with_numbers):
        """正常系: 名前に先頭の番号あり"""
        result = parse_kintai_html(sample_kintai_html_with_numbers)
        assert '太郎' in result  # 先頭の番号が削除される
        assert result['太郎']['hours'] == 8.0

    def test_parse_html_with_spaces(self, sample_kintai_html_with_spaces):
        """正常系: 名前にスペース・全角スペースあり"""
        result = parse_kintai_html(sample_kintai_html_with_spaces)
        assert '太郎' in result  # スペースが削除される
        assert result['太郎']['hours'] == 8.0

    def test_parse_invalid_html(self):
        """エラーケース: 無効なHTML"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.html') as f:
            f.write('<html><body>Invalid HTML</body></html>')
            temp_path = f.name

        try:
            result = parse_kintai_html(temp_path)
            assert result == {}  # 空の辞書が返される
        finally:
            os.unlink(temp_path)

    def test_parse_html_no_table(self):
        """エラーケース: テーブルなしHTML"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.html') as f:
            f.write('<html><body><p>No table here</p></body></html>')
            temp_path = f.name

        try:
            result = parse_kintai_html(temp_path)
            assert result == {}
        finally:
            os.unlink(temp_path)

    def test_parse_html_missing_headers(self, sample_kintai_html_missing_headers):
        """エラーケース: 必要なヘッダーがない"""
        result = parse_kintai_html(sample_kintai_html_missing_headers)
        # ヘッダーがないため、データが抽出されない
        assert result == {}

class TestIntegrationVerifyHours:
    """verify_hours.py の統合テスト"""

    def test_full_parse_flow(self, sample_env_file_verify_hours, sample_kintai_html):
        """正常系: envファイルとHTMLの全フロー"""
        root_dir, results_dir, kintai_dir = parse_env_file(sample_env_file_verify_hours)
        assert os.path.exists(root_dir)

        result = parse_kintai_html(sample_kintai_html)
        assert len(result) > 0
        assert '太郎' in result

class TestVerifyHoursMain:
    """verify_hours.py の main() 関数の統合テスト"""

    def test_main_basic_verification(self, temp_project_dir):
        """正常系: 基本的な勤怠・工数検証"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8', '8'])
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '0', '0'])

        # 勤怠HTMLファイル作成
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>正社員</td><td>8.0</td></tr>
<tr><td>花子</td><td>正社員</td><td>8.0</td></tr>
</table>
</html>''')

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
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        # input() をモック（許容割合を0%に設定）
        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()

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
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
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
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()  # エラーメッセージが出力される

    def test_main_missing_data_file(self, temp_project_dir):
        """エラーケース: raw_data.csv が見当たらない"""
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # 勤怠HTMLファイルのみ作成
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('<table><tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr></table>')

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()  # エラーメッセージが出力される

class TestVerifyHoursIntegration:
    """verify_hours.py の複合テスト"""

    def test_verification_with_matched_data(self, temp_project_dir):
        """正常系: 勤怠と工数が一致"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '10', '10'])
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '6', '6'])

        # 勤怠HTMLファイル作成（16時間 = 10 + 6）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>正社員</td><td>16.0</td></tr>
<tr><td>花子</td><td>正社員</td><td>16.0</td></tr>
</table>
</html>''')

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()

    def test_verification_with_manager_skip(self, temp_project_dir):
        """正常系: マネージャーのスキップ"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8'])

        # 勤怠HTML（太郎は管理者、データなし想定）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>管理職</td><td>0.0</td></tr>
</table>
</html>''')

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()

    def test_verification_with_tolerance_threshold(self, temp_project_dir):
        """正常系: 許容割合の指定"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成（工数が少なめ）
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '7.5'])  # 実働8.0の93.75%

        # 勤怠HTML
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>正社員</td><td>8.0</td></tr>
</table>
</html>''')

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        # 許容割合を5%に設定
        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='5'):
                main()

    def test_verification_with_zero_hours_skip(self, temp_project_dir):
        """正常系: 実働0時間の員はスキップ"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8', '0'])

        # 勤怠HTML（花子は実働0時間 = 休職者等）
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>正社員</td><td>8.0</td></tr>
<tr><td>花子</td><td>正社員</td><td>0.0</td></tr>
</table>
</html>''')

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()

    def test_verification_with_multiple_people(self, temp_project_dir):
        """正常系: 複数人の検証"""
        results_dir = temp_project_dir['results_dir']
        kintai_dir = os.path.join(temp_project_dir['root'], 'kintai')
        os.makedirs(kintai_dir, exist_ok=True)

        # raw_data.csv を作成
        raw_data_path = os.path.join(results_dir, 'raw_data.csv')
        with open(raw_data_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['月', '案件名', '内外製区分', '品区コード', '太郎', '花子', '次郎'])
            writer.writerow(['2026/04', 'ProjectA', 'N', 'code1', '8', '8', '8'])
            writer.writerow(['2026/04', 'ProjectB', 'G', 'code2', '4', '4', '4'])

        # 勤怠HTML
        kintai_html = os.path.join(kintai_dir, '202604_kintai.xls')
        with open(kintai_html, 'w', encoding='utf-8') as f:
            f.write('''<html>
<table>
<tr><th>名前</th><th>雇用区分</th><th>実働時間</th></tr>
<tr><td>太郎</td><td>正社員</td><td>12.0</td></tr>
<tr><td>花子</td><td>正社員</td><td>12.0</td></tr>
<tr><td>次郎</td><td>正社員</td><td>12.0</td></tr>
</table>
</html>''')

        env_path = os.path.join(temp_project_dir['root'], 'test_env')
        with open(env_path, 'w', encoding='cp932') as f:
            f.write(temp_project_dir['root'] + '\n')
            f.write('dummy1\n')
            f.write('member\n')
            f.write('kintai\n')
            f.write('list\n')
            f.write('dummy3\n')
            f.write('results\n')
            f.write('dummy4\n')

        mock_argv = [
            'verify_hours.py',
            '--env', env_path,
            '--data', 'raw_data.csv',
            '--month', '202604'
        ]

        with mock.patch.object(sys, 'argv', mock_argv):
            with mock.patch('builtins.input', return_value='0'):
                main()
