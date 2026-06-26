# -*- coding: utf-8 -*-
r"""derive_inc_list.py

一元マスタ <期>_inc_master.csv を入力に、aggregate_hours.py が読む
<期>_inc_list.csv 形式 (CP932, ヘッダー inc_num,naigaikubun,hinku) へ
射影生成する派生スクリプト。

設計方針:
  - <期>_inc_list.csv は手編集・直接生成せず、inc_master からの「派生物」とする。
  - ただし本番の list/<期>_inc_list.csv は絶対に上書きしない。
    検証用に list/_generated/<期>_inc_list.csv へ出力する。
  - 出力フォーマットは現行 list/<期>_inc_list.csv と完全一致させる
    (列順 inc_num,naigaikubun,hinku / CP932 / 先頭に AUTO-GENERATED 等の
     注記コメント行は付けない)。

射影ルール:
  - code        -> inc_num
  - 内外製       -> naigaikubun  (N/G/K/y)
  - 品区        -> hinku        (例: 32, y10。マスタの品区値をそのまま)
  - 内外製が空のレコードは出力しない
    (現行 inc_list に内外製空のコードは載っていないため整合させる)。
  - 出力は code 昇順。

使い方 (bin から):
  python derive_inc_list.py
  python derive_inc_list.py --periods 188 189
  python derive_inc_list.py --list-dir ..\list --out-dir ..\list\_generated
"""
import argparse
import csv
import os
import sys


# 出力 (= 現行 inc_list) の列順
OUTPUT_HEADER = ['inc_num', 'naigaikubun', 'hinku']

# 現行 inc_list で許容される内外製区分
VALID_NAIGAI = {'N', 'G', 'K', 'y'}


def read_master(master_path):
    """inc_master.csv を読み、dict のリストで返す (ヘッダーをキーに使う)。"""
    with open(master_path, 'r', encoding='cp932', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def derive_records(master_rows):
    """master 行から (inc_num, naigaikubun, hinku) のリストを返す。

    返り値: (records, skipped)
      records : 出力対象の3要素タプル (code 昇順)
      skipped : 内外製が空などで除外したコードのリスト
    """
    records = []
    skipped = []
    for row in master_rows:
        code = (row.get('code') or '').strip()
        naigai = (row.get('内外製') or '').strip()
        hinku = (row.get('品区') or '').strip()
        if code == '':
            continue
        if naigai == '' or naigai not in VALID_NAIGAI:
            skipped.append(code)
            continue
        records.append((code, naigai, hinku))
    records.sort(key=lambda t: int(t[0]))
    return records, skipped


def write_inc_list(records, output_path):
    """3列 CSV (CP932, ヘッダー付き) を出力する。注記コメント行は付けない。"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='cp932', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_HEADER)
        for rec in records:
            writer.writerow(list(rec))
    return len(records)


def derive_one_period(period, list_dir, out_dir):
    """1期分の派生 inc_list を生成する。生成件数を返す (失敗時 None)。"""
    master_path = os.path.join(list_dir, f'{period}_inc_master.csv')
    if not os.path.isfile(master_path):
        print(f"【エラー】{period}_inc_master.csv が見つかりません: {master_path}")
        return None
    master_rows = read_master(master_path)
    records, skipped = derive_records(master_rows)
    if skipped:
        print(f"  【情報】{period}期: 内外製が空/対象外で除外 "
              f"({len(skipped)}件): {', '.join(skipped)}")
    output_path = os.path.join(out_dir, f'{period}_inc_list.csv')
    count = write_inc_list(records, output_path)
    print(f"  {period}_inc_list.csv を生成: {output_path} ({count}件)")
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='inc_master.csv から検証用の inc_list.csv を派生生成する')
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(bin_dir)
    parser.add_argument(
        '--list-dir',
        default=os.path.join(project_root, 'list'),
        help='inc_master.csv の格納ディレクトリ (既定: ../list)')
    parser.add_argument(
        '--out-dir',
        default=os.path.join(project_root, 'list', '_generated'),
        help='出力先ディレクトリ (既定: ../list/_generated)')
    parser.add_argument(
        '--periods', nargs='+', default=['188', '189'],
        help='生成対象の期番号 (既定: 188 189)')
    args = parser.parse_args(argv)

    ok = True
    total = 0
    for period in args.periods:
        count = derive_one_period(period, args.list_dir, args.out_dir)
        if count is None:
            ok = False
        else:
            total += count
    print(f"完了: 合計 {total} 件")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
