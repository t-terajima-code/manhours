# -*- coding: utf-8 -*-
import argparse
import csv
import glob
import os
import sys
import datetime
import re

# --- 単位サニティ警告の閾値（定数） ---
# 1日あたりの合計工数が超えると異常とみなす上限（分）。24時間 = 1440分。
MAX_DAILY_MINUTES = 1440.0
# 1か月あたりの合計工数が、これ未満かつ 0 より大きい場合に「小さすぎる」とみなす下限（時間）。
# 担当者が「時間」で入力すると無条件に /60 され 1/60 に縮むため、その兆候を拾う。
MIN_MONTHLY_HOURS = 1.0


def check_unit_sanity(daily_minutes, monthly_hours):
    """単位ミス（時間入力 → /60 で縮小 等）の兆候を検出して警告メッセージのリストを返す。

    引数:
        daily_minutes: {(month, person, day_serial): 合計分} の dict
        monthly_hours: {(month, person): 合計時間} の dict
    返り値:
        警告文字列のリスト（異常なしなら空リスト）。
    この関数は集計結果（agg_data／出力）には一切影響しない、純粋な検査用。
    """
    warnings = []
    # 日合計 > 24h（=1440分）: 入力過大の疑い
    for (month, person, day_serial), total_min in sorted(daily_minutes.items()):
        if total_min > MAX_DAILY_MINUTES:
            warnings.append(
                f"{month} {person}: 1日の合計が {total_min:.0f}分 "
                f"(>{MAX_DAILY_MINUTES:.0f}分=24h) と過大です（日付シリアル {day_serial}）。単位（分/時間）をご確認ください。"
            )
    # 月合計 < 1h かつ > 0: 「時間」入力を /60 した縮小の疑い
    for (month, person), total_h in sorted(monthly_hours.items()):
        if 0 < total_h < MIN_MONTHLY_HOURS:
            warnings.append(
                f"{month} {person}: 月の合計が {total_h:.3f}時間 "
                f"(<{MIN_MONTHLY_HOURS:.0f}h) と過小です。「時間」単位で入力していないかご確認ください（本システムは分入力を想定）。"
            )
    return warnings

def parse_env_file(env_file_path):
    """envファイル(CP932)を読み込み、入出力ディレクトリの絶対パスを返す。

    envファイルの行構成（最低8行必要）:
        1行目: ルートディレクトリ（絶対パス）
        3行目: member サブディレクトリ名（担当者工数CSVの格納先）
        5行目: list サブディレクトリ名（マスタCSVの格納先）
        7行目: results サブディレクトリ名（出力先）

    可搬性: 1行目の絶対パスが実在しない場合（別PC・別ドライブへ配布・移動した等）は、
    envの場所（bin/）の親ディレクトリ＝パッケージルートを自動採用してフォールバックする。
    これにより env を書き換えなくても展開先で動作する。

    引数:
        env_file_path: envファイルのパス。
    返り値:
        (staff_csv_dir, output_dir, master_csv_dir) のタプル。
    例外:
        FileNotFoundError: envファイルが存在しない場合。
        ValueError: 行数が8行未満の場合。
    """
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")
    with open(env_file_path, 'r', encoding='cp932') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if len(lines) < 8:
        raise ValueError("envファイルの行数が不足しています。少なくとも8行必要です。")
    
    # env 1行目の絶対パスを優先。配布先で別PC/別ドライブに移動して 1行目が実在しない場合は、
    # env の場所(bin/)の親=パッケージルートを自動解決して動くようにする。
    _auto_root = os.path.dirname(os.path.dirname(os.path.abspath(env_file_path)))
    root_dir = lines[0] if os.path.isdir(lines[0]) else _auto_root
    staff_csv_dir = os.path.join(root_dir, lines[2].lstrip('\\/'))  # 3行目: \member
    master_csv_dir = os.path.join(root_dir, lines[4].lstrip('\\/')) # 5行目: \list
    output_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))     # 7行目: \results
    
    return staff_csv_dir, output_dir, master_csv_dir

def excel_date_to_month(excel_date):
    """Excelシリアル値（または数値文字列）を 'YYYY/MM' 形式の月文字列に変換する。

    Excelの日付シリアル（基準日 1899/12/30）を解釈する。変換できない値
    （空文字・非数値・ヘッダー文字列等）に対しては None を返す。
    """
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
    """エントリポイント: 担当者工数CSVを集計して raw_data.csv を出力する。

    処理の流れ:
        1. --month（YYYYMM または YYYY/MM）と --env を解釈し、期番号からマスタを選択。
        2. nichijou_list / proj_list / inc_list の各マスタを読み込み、業務名・コード→
           (内外製区分, 品区, カテゴリ) の対応表を構築。
        3. member/ の各担当者CSV（YYYYMM_*.csv）を走査し、入力値（分）を時間に換算（/60）
           して、月×カテゴリ×(業務, 内外製, 品区)×担当者 で集計。
        4. マスタ未登録・単位異常・エンコード不正の各警告を表示。
        5. CP932 で {YYYYMM}_raw_data.csv（--month 指定時）を results/ に出力。

    入力CSVは CP932 前提。CP932 で読めないファイルは既定でスキップし警告（--strict で
    エラー終了）。--month 未指定時は全月を1ファイルに出力する。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', default='env')
    parser.add_argument('--out', default='raw_data.csv')
    parser.add_argument('--month', type=str, default=None, help='出力対象の年月 (例: 202604 または 2026/04)。指定しない場合は全月出力')
    parser.add_argument('--strict', action='store_true',
                        help='厳格モード。member CSV にエンコード不正（UTF-8/BOM等の誤保存）があった場合、'
                             'スキップせずエラー終了する。単位サニティは strict でも警告のみ。')
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
    encode_warnings = []          # エンコード不正でスキップしたファイルの警告
    sanity_daily = {}             # {(month, person, day_serial): 合計分}  サニティ検査専用（出力に不参加）
    sanity_monthly = {}           # {(month, person): 合計時間}            サニティ検査専用（出力に不参加）

    # YYYYMM プレフィックスでフィルタリング（--month 指定時）
    if target_month:
        yyyymm = target_month.replace('/', '')
        staff_files = sorted(glob.glob(os.path.join(staff_csv_dir, f'{yyyymm}_*.csv')))
    else:
        staff_files = sorted(glob.glob(os.path.join(staff_csv_dir, '*.csv')))

    for f_path in staff_files:
        p_name = extract_person_name(f_path)

        # エンコード安全読込: CP932で読めないファイル（UTF-8/BOM付き等の誤保存）は
        # 既定ではスキップしてファイル名付きで警告を収集。--strict 指定時はエラー終了。
        try:
            with open(f_path, 'r', encoding='cp932') as f:
                rows = list(csv.reader(f))
        except UnicodeDecodeError as e:
            msg = (f"{os.path.basename(f_path)}: CP932で読み込めませんでした"
                   f"（UTF-8/BOM付き等で保存されている可能性があります）。{e}")
            if args.strict:
                print(f"\n【エラー】member CSV のエンコードが不正です: {msg}")
                sys.exit(1)
            encode_warnings.append(msg)
            continue

        if p_name not in persons: persons.append(p_name)

        reader = iter(rows)
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
                    raw_val = float(row[i]) if row[i] else 0.0
                except ValueError:
                    raw_val = 0.0
                # 【修正】入力値（分）を60で割り、時間（Hour）に換算する
                h = raw_val / 60.0
                if h == 0: continue

                # --- 単位サニティ検査用の集計（出力には一切影響しない） ---
                sanity_daily[(month, p_name, row[0])] = \
                    sanity_daily.get((month, p_name, row[0]), 0.0) + raw_val
                sanity_monthly[(month, p_name)] = \
                    sanity_monthly.get((month, p_name), 0.0) + h

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

    # 単位サニティ警告（時間入力による縮小・過大入力の兆候）。strict でも警告に留める。
    sanity_warnings = check_unit_sanity(sanity_daily, sanity_monthly)
    if sanity_warnings:
        print("\n【警告】工数の単位に異常の疑いがあります（本システムは「分」入力を想定）")
        for w in sanity_warnings: print(f"  - {w}")

    # エンコード不正でスキップしたファイルのサマリ（既定動作。--strict 時はここに到達しない）
    if encode_warnings:
        print("\n【警告】以下の member CSV はエンコード不正のためスキップしました（集計から除外）")
        for w in encode_warnings: print(f"  - {w}")

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