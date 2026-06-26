# -*- coding: utf-8 -*-
"""build_inc_name_list.py のテスト。

fixture はこのファイル内にローカル定義する (conftest.py は編集しない)。
"""
import csv
import os
import sys

import pytest

# bin/ を import path に追加
BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

import build_inc_name_list as binl  # noqa: E402


# ---------------------------------------------------------------------------
# ローカル fixture
# ---------------------------------------------------------------------------
def _write_member_csv(path, name_row, code_row):
    """member 形式の CSV (1行目=名前, 2行目=コード) を CP932 で書く。"""
    with open(path, 'w', encoding='cp932', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(name_row)
        writer.writerow(code_row)


@pytest.fixture
def member_dir(tmp_path):
    """member CSV を置く一時ディレクトリ。"""
    d = tmp_path / 'member'
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# normalize_code
# ---------------------------------------------------------------------------
def test_normalize_code_plain():
    assert binl.normalize_code('188037') == '188037'


def test_normalize_code_float_string():
    # float 化されたコードは整数化される
    assert binl.normalize_code('188037.0') == '188037'


def test_normalize_code_with_spaces():
    assert binl.normalize_code('  188037.0  ') == '188037'


def test_normalize_code_empty_is_none():
    assert binl.normalize_code('') is None
    assert binl.normalize_code('   ') is None
    assert binl.normalize_code(None) is None


def test_normalize_code_non_numeric_is_none():
    assert binl.normalize_code('abc') is None


# ---------------------------------------------------------------------------
# extract_yyyymm
# ---------------------------------------------------------------------------
def test_extract_yyyymm():
    assert binl.extract_yyyymm('202504_A青山.csv') == '202504'
    assert binl.extract_yyyymm(r'C:\x\202504_A青山.csv') == '202504'
    assert binl.extract_yyyymm('noprefix.csv') is None


# ---------------------------------------------------------------------------
# collect_names
# ---------------------------------------------------------------------------
def test_collect_basic_mapping(member_dir):
    """date,holiday の先頭2列は無視し、code→name が取れる。"""
    _write_member_csv(
        os.path.join(str(member_dir), '202504_A甲.csv'),
        ['date', 'holiday', 'ロール関係', '電気関係'],
        ['', '', '188037', '188040'],
    )
    result = binl.collect_names(str(member_dir))
    assert result['188037'][0] == 'ロール関係'
    assert result['188040'][0] == '電気関係'


def test_collect_skips_empty_code_columns(member_dir):
    """コード空欄の列 (nichijou/proj 系) は対象外。"""
    _write_member_csv(
        os.path.join(str(member_dir), '202504_A甲.csv'),
        ['date', 'holiday', '週報記入', 'ロール関係'],
        ['', '', '', '188037'],
    )
    result = binl.collect_names(str(member_dir))
    assert '188037' in result
    assert len(result) == 1  # 空欄列は入らない


def test_collect_float_code_integerized(member_dir):
    """float 化されたコードが整数化される。"""
    _write_member_csv(
        os.path.join(str(member_dir), '202504_A甲.csv'),
        ['date', 'holiday', 'ロール関係'],
        ['', '', '188037.0'],
    )
    result = binl.collect_names(str(member_dir))
    assert '188037' in result
    assert '188037.0' not in result


def test_collect_strips_name_whitespace(member_dir):
    _write_member_csv(
        os.path.join(str(member_dir), '202504_A甲.csv'),
        ['date', 'holiday', '  ロール関係  '],
        ['', '', '188037'],
    )
    result = binl.collect_names(str(member_dir))
    assert result['188037'][0] == 'ロール関係'


def test_collect_newer_yyyymm_wins(member_dir):
    """同一コードで年月が新しい方の表示名を採用する。"""
    # 古い (202401): 旧名
    _write_member_csv(
        os.path.join(str(member_dir), '202401_A甲.csv'),
        ['date', 'holiday', '旧ロール'],
        ['', '', '188037'],
    )
    # 新しい (202504): 新名
    _write_member_csv(
        os.path.join(str(member_dir), '202504_B乙.csv'),
        ['date', 'holiday', '新ロール'],
        ['', '', '188037'],
    )
    result = binl.collect_names(str(member_dir))
    assert result['188037'][0] == '新ロール'


def test_collect_older_does_not_override_newer(member_dir):
    """ファイル処理順に依らず、新しい年月が必ず勝つ (古いファイルが後でも上書きしない)。"""
    # 新しい (202504) を先に、古い (202401) を後に書いても結果は新しい方
    _write_member_csv(
        os.path.join(str(member_dir), '202504_B乙.csv'),
        ['date', 'holiday', '新ロール'],
        ['', '', '188037'],
    )
    _write_member_csv(
        os.path.join(str(member_dir), '202401_A甲.csv'),
        ['date', 'holiday', '旧ロール'],
        ['', '', '188037'],
    )
    result = binl.collect_names(str(member_dir))
    assert result['188037'][0] == '新ロール'


# ---------------------------------------------------------------------------
# write_inc_name_list (出力契約)
# ---------------------------------------------------------------------------
def test_write_output_contract(tmp_path):
    """CP932・ヘッダー inc_num,name・コード昇順・2列を満たす。"""
    name_map = {
        '188040': ('電気関係', '202504'),
        '188037': ('ロール関係', '202504'),
        '188100': ('印材関係', '202504'),
    }
    out = os.path.join(str(tmp_path), 'inc_name_list.csv')
    count = binl.write_inc_name_list(name_map, out)
    assert count == 3

    # CP932 で読めること
    with open(out, 'r', encoding='cp932', newline='') as f:
        rows = list(csv.reader(f))

    assert rows[0] == ['inc_num', 'name']
    # 全データ行が2列
    for r in rows[1:]:
        assert len(r) == 2
    # コード昇順
    codes = [r[0] for r in rows[1:]]
    assert codes == ['188037', '188040', '188100']
    assert rows[1] == ['188037', 'ロール関係']


def test_write_output_is_cp932_not_utf8(tmp_path):
    """日本語を含む出力が CP932 であり、UTF-8 では復号できない (取り違え検知)。"""
    name_map = {'188037': ('ロール関係', '202504')}
    out = os.path.join(str(tmp_path), 'inc_name_list.csv')
    binl.write_inc_name_list(name_map, out)

    raw = open(out, 'rb').read()
    # CP932 では問題なく復号できる
    raw.decode('cp932')
    # UTF-8 として復号すると日本語部分でエラーになるはず
    with pytest.raises(UnicodeDecodeError):
        raw.decode('utf-8')


# ---------------------------------------------------------------------------
# main (エンドツーエンド)
# ---------------------------------------------------------------------------
def test_main_end_to_end(tmp_path, capsys):
    member_dir = tmp_path / 'member'
    member_dir.mkdir()
    list_dir = tmp_path / 'list'
    list_dir.mkdir()
    _write_member_csv(
        os.path.join(str(member_dir), '202504_A甲.csv'),
        ['date', 'holiday', 'ロール関係', '電気関係'],
        ['', '', '188037.0', '188040'],
    )
    out = os.path.join(str(list_dir), 'inc_name_list.csv')

    rc = binl.main(['--member-dir', str(member_dir),
                    '--output', out,
                    '--list-dir', str(list_dir)])
    assert rc == 0
    assert os.path.exists(out)

    with open(out, 'r', encoding='cp932', newline='') as f:
        rows = list(csv.reader(f))
    assert rows[0] == ['inc_num', 'name']
    data = {r[0]: r[1] for r in rows[1:]}
    assert data == {'188037': 'ロール関係', '188040': '電気関係'}


def test_main_missing_member_dir(tmp_path, capsys):
    rc = binl.main(['--member-dir', os.path.join(str(tmp_path), 'nope'),
                    '--output', os.path.join(str(tmp_path), 'o.csv'),
                    '--list-dir', str(tmp_path)])
    assert rc == 1
