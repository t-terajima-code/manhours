# -*- coding: utf-8 -*-
r"""build_inc_name_list_from_master.py

インシデント管理表.xlsx 由来の一元マスタ list/<期>_inc_master.csv 群から
「インシデントコード → 案件名」の正引きマスタ list/inc_name_list.csv
(CP932, ヘッダー inc_num,name) を再生成する。

inc_master CSV の構造 (CP932):
  - 1行目ヘッダー: code,name,内外製,品区,...(任意列)
  - 2行目以降: code(列0), name(列1), ...
  - name 列は複数行セル(改行入り)を含むため csv モジュールで正しくパースする。

出力契約 (既存 inc_name_list.csv の流儀に合わせる):
  - list/inc_name_list.csv, CP932, ヘッダー行 inc_num,name
  - 1コード1行、コード昇順 (数値順)、name は前後空白除去
  - name が空のコードは出力しない (従来 inc_name_list.csv に空 name 行は無い)
  - 同一コードが複数の master に出る場合、新しい期 (189>188) の name を優先

bin から実行:
  python build_inc_name_list_from_master.py
  python build_inc_name_list_from_master.py --master 188_inc_master.csv 189_inc_master.csv
"""
import argparse
import csv
import glob
import os
import re
import sys


# ファイル名先頭の期 (188 / 189 ...) を取り出す
_FY_RE = re.compile(r'(\d+)_inc_master\.csv$')


def extract_fy(path):
    """master ファイル名から期番号 (int) を返す。取れなければ -1。"""
    m = _FY_RE.search(os.path.basename(path))
    if m:
        return int(m.group(1))
    return -1


def normalize_code(raw):
    """コード文字列を整数文字列に正規化する。空欄/非数値は None。"""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == '':
        return None
    s = s.split('.')[0]
    if not s.isdigit():
        return None
    return str(int(s))


def collect_from_master(master_paths):
    """master CSV 群を読み、{コード: (name, fy)} を返す。

    同一コードに複数 master があれば期 (fy) が大きい方を優先 (189>188)。
    """
    result = {}  # code -> (name, fy)
    for path in master_paths:
        fy = extract_fy(path)
        try:
            with open(path, 'r', encoding='cp932', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None:
                    continue
                for row in reader:
                    if len(row) < 2:
                        continue
                    code = normalize_code(row[0])
                    if code is None:
                        continue
                    name = row[1].strip()
                    if name == '':
                        # 空 name のコードは出力しない (従来仕様)
                        continue
                    prev = result.get(code)
                    if prev is None or fy >= prev[1]:
                        result[code] = (name, fy)
        except (OSError, UnicodeDecodeError) as e:
            print(f"【警告】読み込み失敗のためスキップ: {os.path.basename(path)} ({e})")
            continue
    return result


def write_inc_name_list(name_map, output_path):
    """{コード: (name, fy)} を CP932 / inc_num,name の2列 CSV に出力。"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    codes = sorted(name_map.keys(), key=lambda c: int(c))
    with open(output_path, 'w', encoding='cp932', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['inc_num', 'name'])
        for code in codes:
            writer.writerow([code, name_map[code][0]])
    return len(codes)


def main(argv=None):
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(bin_dir)
    list_dir = os.path.join(project_root, 'list')

    parser = argparse.ArgumentParser(
        description='inc_master CSV から inc_name_list.csv を再生成する')
    parser.add_argument(
        '--master', nargs='+', default=None,
        help='入力 master CSV (list/ 配下の名前 or 絶対パス)。'
             '既定: list/*_inc_master.csv を全て使用')
    parser.add_argument(
        '--output',
        default=os.path.join(list_dir, 'inc_name_list.csv'),
        help='出力先 (既定: list/inc_name_list.csv)')
    args = parser.parse_args(argv)

    if args.master:
        master_paths = []
        for m in args.master:
            master_paths.append(m if os.path.isabs(m) else os.path.join(list_dir, m))
    else:
        master_paths = sorted(glob.glob(os.path.join(list_dir, '*_inc_master.csv')))

    if not master_paths:
        print("【エラー】inc_master CSV が見つかりません。")
        return 1
    for p in master_paths:
        if not os.path.isfile(p):
            print(f"【エラー】master が見つかりません: {p}")
            return 1

    name_map = collect_from_master(master_paths)
    count = write_inc_name_list(name_map, args.output)
    print(f"inc_name_list.csv を生成しました: {args.output}")
    print(f"  入力 master: {', '.join(os.path.basename(p) for p in master_paths)}")
    print(f"  出力コード件数: {count}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
