# -*- coding: utf-8 -*-
r"""build_inc_name_list.py

過去の member CSV から「インシデントコード → 業務表示名」の正引きマスタを
自動収集し、list/inc_name_list.csv (CP932, ヘッダー inc_num,name) を生成する。

member CSV の構造:
  - member/YYYYMM_<イニシャル><氏名>.csv (CP932)
  - 1行目 = 業務表示名 (列index2以降が業務、先頭2列は date,holiday)
  - 2行目 = コード (例 188037, "188037.0" のように float 化しうる)
  - 同一コードに複数の表示名があり得る → ファイル名の YYYYMM が新しいものを優先
  - コードが空欄の列 (nichijou/proj 系) は対象外

出力契約:
  - list/inc_name_list.csv, CP932, ヘッダー行 inc_num,name
  - 1コード1行、コード昇順、name は前後空白除去

使い方 (bin から):
  python build_inc_name_list.py
  python build_inc_name_list.py --member-dir ..\member --output ..\list\inc_name_list.csv
"""
import argparse
import csv
import glob
import os
import re
import sys


# ファイル名先頭の YYYYMM を取り出す正規表現
_YYYYMM_RE = re.compile(r'^(\d{6})_')


def extract_yyyymm(filename):
    """member ファイル名 (basename) 先頭の YYYYMM を返す。取れなければ None。"""
    m = _YYYYMM_RE.match(os.path.basename(filename))
    if m:
        return m.group(1)
    return None


def normalize_code(raw):
    """コード文字列を整数文字列に正規化する。

    "188037.0" のような float 化された値は ".0" を落として "188037" にする。
    空欄や数値でないものは None を返す (対象外)。
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == '':
        return None
    # "188037.0" → "188037"
    s = s.split('.')[0]
    if not s.isdigit():
        return None
    return str(int(s))


def collect_names(member_dir):
    """member_dir 内の全 *.csv をスキャンし、{コード: (表示名, 出典YYYYMM)} を返す。

    同一コードに複数の表示名がある場合、ファイル名 YYYYMM が新しいものを優先する。
    """
    result = {}  # code -> (name, yyyymm)
    files = sorted(glob.glob(os.path.join(member_dir, '*.csv')))

    for path in files:
        yyyymm = extract_yyyymm(path)
        if yyyymm is None:
            # YYYYMM プレフィックスを持たないファイルは対象外
            continue
        try:
            with open(path, 'r', encoding='cp932', newline='') as f:
                reader = csv.reader(f)
                rows = []
                for i, row in enumerate(reader):
                    rows.append(row)
                    if i >= 1:  # 1行目(名前) と 2行目(コード) があれば十分
                        break
        except (OSError, UnicodeDecodeError) as e:
            print(f"【警告】読み込み失敗のためスキップ: {os.path.basename(path)} ({e})")
            continue

        if len(rows) < 2:
            continue

        name_row = rows[0]
        code_row = rows[1]

        # 列index2以降が業務 (先頭2列は date,holiday)
        for col in range(2, min(len(name_row), len(code_row))):
            code = normalize_code(code_row[col])
            if code is None:
                continue
            name = name_row[col].strip()
            if name == '':
                continue
            prev = result.get(code)
            # より新しい (もしくは同月で後勝ち) なら更新
            if prev is None or yyyymm >= prev[1]:
                result[code] = (name, yyyymm)

    return result


def write_inc_name_list(name_map, output_path):
    """{コード: (表示名, YYYYMM)} を CP932 / inc_num,name の2列 CSV に出力する。"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    # コード昇順 (数値順)
    codes = sorted(name_map.keys(), key=lambda c: int(c))
    with open(output_path, 'w', encoding='cp932', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['inc_num', 'name'])
        for code in codes:
            writer.writerow([code, name_map[code][0]])
    return len(codes)


def load_master_codes(list_dir):
    """list/<期>_inc_list.csv 群から inc_num の集合を読み込んで返す。

    突合用。読めない/無ければ空集合。
    """
    codes = set()
    for path in glob.glob(os.path.join(list_dir, '*inc_list.csv')):
        try:
            with open(path, 'r', encoding='cp932', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # ヘッダー
                for row in reader:
                    if row:
                        c = normalize_code(row[0])
                        if c is not None:
                            codes.add(c)
        except (OSError, UnicodeDecodeError):
            continue
    return codes


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='member CSV から inc_name_list.csv (正引きマスタ) を生成する')
    # bin から実行する想定で、既定は bin の1つ上 (プロジェクトルート) を基準にする
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(bin_dir)
    parser.add_argument(
        '--member-dir',
        default=os.path.join(project_root, 'member'),
        help='member CSV の格納ディレクトリ (既定: ../member)')
    parser.add_argument(
        '--output',
        default=os.path.join(project_root, 'list', 'inc_name_list.csv'),
        help='出力先 (既定: ../list/inc_name_list.csv)')
    parser.add_argument(
        '--list-dir',
        default=os.path.join(project_root, 'list'),
        help='突合用マスタ (*_inc_list.csv) の格納ディレクトリ (既定: ../list)')
    args = parser.parse_args(argv)

    if not os.path.isdir(args.member_dir):
        print(f"【エラー】member ディレクトリが見つかりません: {args.member_dir}")
        return 1

    name_map = collect_names(args.member_dir)
    count = write_inc_name_list(name_map, args.output)
    print(f"inc_name_list.csv を生成しました: {args.output}")
    print(f"  収集コード件数: {count}")

    # --- 任意: 期マスタとの突合 ---
    if os.path.isdir(args.list_dir):
        master_codes = load_master_codes(args.list_dir)
        if master_codes:
            collected = set(name_map.keys())
            # マスタにあるが member から名前が取れなかったコード
            no_name = sorted(master_codes - collected, key=lambda c: int(c))
            # member にあるがマスタに無いコード
            not_in_master = sorted(collected - master_codes, key=lambda c: int(c))
            print(f"  マスタ(*_inc_list.csv) コード件数: {len(master_codes)}")
            if no_name:
                print(f"  【警告】名前が取れなかったコード ({len(no_name)}件): "
                      f"{', '.join(no_name[:20])}{' ...' if len(no_name) > 20 else ''}")
            if not_in_master:
                print(f"  【情報】member にあるがマスタに無いコード ({len(not_in_master)}件): "
                      f"{', '.join(not_in_master[:20])}{' ...' if len(not_in_master) > 20 else ''}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
