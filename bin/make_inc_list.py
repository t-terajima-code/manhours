# -*- coding: utf-8 -*-
"""
インシデント管理表.xlsx から事業年度別の <期>_inc_list.csv を生成する。

各「◆XXX期」シートを走査し、ｲﾝｼﾃﾞﾝﾄ№/ＮＧＫｙ/品区 を抽出して
list/<期>_inc_list.csv (CP932, header: inc_num,naigaikubun,hinku) を出力する。
"""
import argparse
import csv
import os
import re
import openpyxl

DEFAULT_XLSX = "インシデント管理表.xlsx"
VALID_NAIGAI = {'N', 'G', 'K', 'y', 'Y'}


def parse_env_file(env_file_path):
    """envファイル: 1行目=root, 5行目(index 4)=list"""
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")
    with open(env_file_path, 'r', encoding='cp932') as f:
        lines = [line.strip() for line in f if line.strip()]
    if len(lines) < 5:
        raise ValueError("envファイルの行数が不足しています。")
    root_dir = lines[0]
    list_dir = os.path.join(root_dir, lines[4].lstrip('\\/'))
    return root_dir, list_dir


def extract_period(sheet_name):
    """'◆189期' から 189 を取り出す。マッチしなければ None。"""
    m = re.match(r'^◆(\d+)期$', sheet_name.strip())
    return int(m.group(1)) if m else None


def detect_header(ws):
    """ヘッダー行を探し、(header_row_idx, {key: col_idx}) を返す。"""
    targets = {
        'inc_num': lambda s: 'ｲﾝｼﾃﾞﾝﾄ' in s or 'インシデント' in s,
        'naigai': lambda s: 'ＮＧＫ' in s or 'NGK' in s.upper(),
        'hinku': lambda s: s == '品区',
    }
    for row_idx in range(1, min(15, ws.max_row + 1)):
        cols = {}
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row_idx, c).value
            if v is None:
                continue
            s = str(v).strip()
            for key, matcher in targets.items():
                if key not in cols and matcher(s):
                    cols[key] = c
        if all(k in cols for k in targets):
            return row_idx, cols
    raise ValueError("ヘッダー行（ｲﾝｼﾃﾞﾝﾄ№/ＮＧＫｙ/品区）が見つかりません。")


def normalize_int_str(v):
    """セル値を「整数文字列」に正規化。float なら小数点以下を落とす。"""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v).strip()


def extract_data(ws, sheet_name):
    """シートから (inc_num, naigai, hinku) のリストとエラー一覧を返す。"""
    header_row, cols = detect_header(ws)
    data = []
    errors = []
    seen = {}  # inc_num -> (row_idx, naigai, hinku)

    for row_idx in range(header_row + 1, ws.max_row + 1):
        inc_raw = ws.cell(row_idx, cols['inc_num']).value
        naigai_raw = ws.cell(row_idx, cols['naigai']).value
        hinku_raw = ws.cell(row_idx, cols['hinku']).value

        # 全カラム空 → 空行としてスキップ（エラーにしない）
        if inc_raw is None and naigai_raw is None and hinku_raw is None:
            continue

        # 各セルの空チェック
        if inc_raw is None or str(inc_raw).strip() == '':
            errors.append(f"  [{sheet_name}] 行{row_idx}: インシデント№が空 (ＮＧＫｙ={naigai_raw}, 品区={hinku_raw})")
            continue
        if naigai_raw is None or str(naigai_raw).strip() == '':
            errors.append(f"  [{sheet_name}] 行{row_idx}: ＮＧＫｙが空 (ｲﾝｼﾃﾞﾝﾄ№={inc_raw}, 品区={hinku_raw})")
            continue
        if hinku_raw is None or str(hinku_raw).strip() == '':
            errors.append(f"  [{sheet_name}] 行{row_idx}: 品区が空 (ｲﾝｼﾃﾞﾝﾄ№={inc_raw}, ＮＧＫｙ={naigai_raw})")
            continue

        # 正規化
        inc_num = normalize_int_str(inc_raw)
        naigai = str(naigai_raw).strip()
        hinku = normalize_int_str(hinku_raw)

        # ＮＧＫｙ の値域チェック
        if naigai not in VALID_NAIGAI:
            errors.append(f"  [{sheet_name}] 行{row_idx}: ＮＧＫｙ='{naigai}' は無効 (許容: N,G,K,y)")
            continue

        # 重複チェック
        if inc_num in seen:
            prev_row, prev_n, prev_h = seen[inc_num]
            if prev_n != naigai or prev_h != hinku:
                errors.append(
                    f"  [{sheet_name}] 行{row_idx}: ｲﾝｼﾃﾞﾝﾄ№={inc_num} 値矛盾 "
                    f"(前回行{prev_row}: {prev_n}/{prev_h}, 今回: {naigai}/{hinku})"
                )
                continue
            # 同一値の重複は黙ってスキップ
            continue

        seen[inc_num] = (row_idx, naigai, hinku)
        data.append((inc_num, naigai, hinku))

    return data, errors


def write_csv(out_path, data):
    with open(out_path, 'w', encoding='cp932', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['inc_num', 'naigaikubun', 'hinku'])
        for row in data:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description='インシデント管理表から <期>_inc_list.csv を生成')
    parser.add_argument('--env', type=str, default='env')
    parser.add_argument('--period', type=int, default=None,
                        help='対象の期番号（例: 189）。未指定なら ◆XXX期 シートを全件処理')
    parser.add_argument('--xlsx', type=str, default=None,
                        help='インシデント管理表.xlsx のパス。未指定ならルート直下を使用')
    args = parser.parse_args()

    try:
        root_dir, list_dir = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】{e}")
        return

    xlsx_path = args.xlsx or os.path.join(root_dir, DEFAULT_XLSX)
    if not os.path.exists(xlsx_path):
        print(f"【エラー】インシデント管理表が見つかりません: {xlsx_path}")
        return

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    # 対象シート選定
    targets = []
    for sheet_name in wb.sheetnames:
        period = extract_period(sheet_name)
        if period is None:
            continue
        if args.period is not None and period != args.period:
            continue
        targets.append((sheet_name, period))

    if not targets:
        if args.period is not None:
            print(f"【エラー】◆{args.period}期 シートが見つかりません。")
        else:
            print("【エラー】◆XXX期 パターンのシートが一つも見つかりません。")
        return

    # 全シートを先に走査し、エラーが無いことを確認してから書き込む
    all_errors = []
    results = []
    for sheet_name, period in targets:
        ws = wb[sheet_name]
        try:
            data, errors = extract_data(ws, sheet_name)
        except ValueError as e:
            print(f"【エラー】シート '{sheet_name}': {e}")
            return
        all_errors.extend(errors)
        results.append((sheet_name, period, data))

    if all_errors:
        print("【エラー】以下の不正データを修正してから再実行してください:")
        for err in all_errors:
            print(err)
        return

    # 書き込み（無言で上書き）
    for sheet_name, period, data in results:
        out_path = os.path.join(list_dir, f"{period}_inc_list.csv")
        write_csv(out_path, data)
        print(f"出力完了: {out_path} ({len(data)}件, シート={sheet_name})")


if __name__ == "__main__":
    main()
