# -*- coding: utf-8 -*-
import argparse
import csv
import glob
import os
import datetime
import re

def parse_env_file(env_file_path):
    """
    envファイルを読み込み、ディレクトリ構成を取得する
    1行目：ルート / 3行目：member / 5行目：list / 7行目：results
    """
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")
    with open(env_file_path, 'r', encoding='cp932') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if len(lines) < 8:
        raise ValueError("envファイルの行数が不足しています。少なくとも8行必要です。")
    
    root_dir = lines[0]
    staff_csv_dir = os.path.join(root_dir, lines[2].lstrip('\\/'))  # 3行目: \member
    master_csv_dir = os.path.join(root_dir, lines[4].lstrip('\\/')) # 5行目: \list
    output_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))     # 7行目: \results
    
    return staff_csv_dir, output_dir, master_csv_dir

def excel_date_to_month(excel_date):
    try:
        val = int(float(excel_date))
        dt = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=val)
        return dt.strftime('%Y/%m')
    except: return None

def compute_fiscal_year(target_month):
    """target_month (YYYY/MM形式) から事業年度（期）番号を計算する。
    188期=2025/4-2026/3, 189期=2026/4-2027/3
    target_month が None のときは None を返す。
    """
    if not target_month:
        return None
    yyyy, mm = target_month.split('/')
    return int(yyyy) - (1837 if int(mm) >= 4 else 1838)


def get_master_files(master_dir, pattern, fiscal_year):
    """マスタファイルを取得。fiscal_year 指定時は <期>_<pattern> 限定で、見つからなければ None。
    fiscal_year=None なら *<pattern> の glob 結果を返す。"""
    if fiscal_year is not None:
        fp = os.path.join(master_dir, f"{fiscal_year}_{pattern}")
        return [fp] if os.path.exists(fp) else None
    import glob as _glob
    return _glob.glob(os.path.join(master_dir, f"*{pattern}"))


def extract_person_name(filename):
    """
    例1: _W渡邊聖.csv -> 渡邊聖 
    例2: 3_T平杜夢.csv -> 平杜夢
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    if '_' in base:
        parts = base.rsplit('_', 1)
        name_part = parts[-1]
        name_clean = re.sub(r'^[a-zA-Z0-9]+', '', name_part)
        return name_clean
    return base

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', default='env')
    parser.add_argument('--out', default='raw_data.csv')
    parser.add_argument('--month', type=str, default=None, help='出力対象の年月 (例: 202604 または 2026/04)。指定しない場合は全月出力')
    args = parser.parse_args()

    # 月フォーマットの統一 (202604 -> 2026/04)
    target_month = None
    if args.month:
        m = args.month.replace('-', '/').replace('/', '')
        if len(m) == 6 and m.isdigit():
            target_month = f"{m[:4]}/{m[4:]}"
        else:
            print(f"【エラー】--month の形式が正しくありません: {args.month}")
            return

    try:
        staff_csv_dir, output_dir, master_csv_dir = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】{e}"); return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- 1. 各種マスタの読み込み ---
    fiscal_year = compute_fiscal_year(target_month)
    task_master = {}

    for pattern, key_col, val_cols, cat in [
        ("nichijou_list.csv", 2, (0, 1), 1),
        ("proj_list.csv", 0, (2, 3), 2),
        ("inc_list.csv", 0, (1, 2), 3),
    ]:
        files = get_master_files(master_csv_dir, pattern, fiscal_year)
        if files is None:
            print(f"【エラー】期{fiscal_year}: マスタファイルが見つかりません: {fiscal_year}_{pattern}")
            return
        min_cols = max(key_col, *val_cols) + 1
        for f in files:
            with open(f, 'r', encoding='cp932') as sf:
                reader = csv.reader(sf)
                next(reader, None)
                for row in reader:
                    if len(row) >= min_cols:
                        task_master[row[key_col].strip()] = (row[val_cols[0]].strip(), row[val_cols[1]].strip(), cat)

    # --- 2. 担当者CSVの集計 ---
    agg_data = {}
    persons = []
    missing_tasks = set()

    # YYYYMM プレフィックスでフィルタリング（--month 指定時）
    if target_month:
        yyyymm = target_month.replace('/', '')
        staff_files = sorted(glob.glob(os.path.join(staff_csv_dir, f'{yyyymm}_*.csv')))
    else:
        staff_files = sorted(glob.glob(os.path.join(staff_csv_dir, '*.csv')))

    for f_path in staff_files:
        p_name = extract_person_name(f_path)
        if p_name not in persons: persons.append(p_name)
        
        with open(f_path, 'r', encoding='cp932') as f:
            reader = csv.reader(f)
            header_names = next(reader, None) # 1行目: 業務名
            header_codes = next(reader, None) # 2行目: インシデントコード等
            if not header_names: continue
            
            for row in reader:
                if not row or not row[0]: continue
                month = excel_date_to_month(row[0])
                if not month: continue
                
                if month not in agg_data:
                    agg_data[month] = {1: {}, 2: {}, 3: {}, 4: {}}
                
                for i in range(2, len(header_names)):
                    if i >= len(row): break
                    
                    display_name = header_names[i].strip()
                    
                    # 2行目のコード取得と成形 (例: "188037.0" -> "188037")
                    raw_code = header_codes[i].strip() if header_codes and i < len(header_codes) else ""
                    code = ""
                    if raw_code and raw_code.lower() not in ['nan', 'none']:
                        code = raw_code.split('.')[0]
                    
                    if not display_name and not code: continue
                    
                    try:
                        # 【修正】入力値（分）を60で割り、時間（Hour）に換算する
                        h = (float(row[i]) / 60.0) if row[i] else 0.0
                    except ValueError: h = 0.0
                    if h == 0: continue
                    
                    # 照合キーと出力名の決定
                    task_key = code if code else display_name
                    
                    naigai, hinku, cat = task_master.get(task_key, ("", "", 4))
                    
                    if cat == 4: missing_tasks.add(task_key)
                    
                    agg_key = (task_key, naigai, hinku)
                    
                    if agg_key not in agg_data[month][cat]:
                        agg_data[month][cat][agg_key] = {'hours': {}}
                    
                    agg_data[month][cat][agg_key]['hours'][p_name] = agg_data[month][cat][agg_key]['hours'].get(p_name, 0.0) + h

    # --- 3. 警告表示と書き出し ---
    if missing_tasks:
        print("\n【警告】以下の業務/コードがマスタに未登録です（内外製・品区が空欄になります）")
        for t in sorted(missing_tasks): print(f"  - {t}")

    if not agg_data:
        print("集計対象のデータが見つかりませんでした。"); return

    # target_month 指定時は、その月に工数データを持つ担当者のみに persons を絞る
    if target_month and target_month in agg_data:
        persons_with_data = set()
        for cat in [1, 2, 3, 4]:
            for agg_item in agg_data[target_month][cat].values():
                persons_with_data.update(agg_item['hours'].keys())
        persons = [p for p in persons if p in persons_with_data]

    out_header = ['月', '案件（業務）名', '内外製区分', '品区コード'] + persons
    out_filename = f"{target_month.replace('/', '')}_raw_data.csv" if target_month and args.out == 'raw_data.csv' else args.out
    output_file = os.path.join(output_dir, out_filename)
    
    months_to_write = sorted(agg_data.keys())
    if target_month:
        if target_month not in agg_data:
            print(f"【警告】指定された月 ({target_month}) のデータが見つかりませんでした。")
            return
        months_to_write = [target_month]

    with open(output_file, 'w', newline='', encoding='cp932') as f:
        writer = csv.writer(f)
        writer.writerow(out_header)
        for month in months_to_write:
            for cat in [1, 2, 3, 4]:
                for agg_key in sorted(agg_data[month][cat].keys()):
                    t_name, naigai, hinku = agg_key
                    row_out = [month, t_name, naigai, hinku]
                    for p in persons:
                        row_out.append(agg_data[month][cat][agg_key]['hours'].get(p, 0.0))
                    writer.writerow(row_out)

    print(f"\n集計完了: {output_file} (分 → 時間 に換算して出力しました)")

if __name__ == "__main__":
    main()