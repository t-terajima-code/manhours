# -*- coding: utf-8 -*-
import argparse
import csv
import os
import glob

def parse_env_file(env_file_path):
    """
    envファイルを読み込み、ディレクトリ構成を取得する
    1行目：ルート / 5行目：list / 7行目：results
    """
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")
        
    with open(env_file_path, 'r', encoding='cp932') as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if len(lines) < 8:
        raise ValueError("envファイルの行数が不足しています。少なくとも8行必要です。")
        
    root_dir = lines[0]
    # 5行目(index 4)が list ディレクトリ（マスタファイル）
    master_dir = os.path.join(root_dir, lines[4].lstrip('\\/'))
    # 7行目(index 6)が results ディレクトリ
    results_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))
    
    return results_dir, master_dir

def compute_fiscal_year(target_month):
    """target_month (YYYY/MM形式) から事業年度（期）番号を計算する。"""
    yyyy, mm = target_month.split('/')
    return int(yyyy) - (1837 if int(mm) >= 4 else 1838)


def is_target_record(naigai, hinku):
    """
    抽出対象か判定する
    - N, G, K の場合はすべて対象
    - y の場合は、品区コードが y1, y10, y20 のいずれかのみ対象
    """
    k = naigai.strip()
    h = hinku.strip()
    
    if k in {'N', 'G', 'K'}:
        return True
    elif k in {'y', 'Y'}:
        if h in {'y1', 'y10', 'y20'}:
            return True
            
    return False

def main():
    parser = argparse.ArgumentParser(description='経理提出用CSVエクスポートツール')
    parser.add_argument('--month', type=str, required=True, help='対象の年月 (例: 202603)')
    parser.add_argument('--env', type=str, default='env', help='設定ファイルのパス')
    parser.add_argument('--data', type=str, default='raw_data.csv', help='入力データファイル名')
    args = parser.parse_args()

    # 月のフォーマット統一
    target_month = args.month.replace('-', '/')
    if len(target_month) == 6 and target_month.isdigit():
        target_month = f"{target_month[:4]}/{target_month[4:]}"
    month_str = target_month.replace('/', '')

    # 1. ディレクトリの取得
    try:
        results_dir, master_dir = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】{e}")
        return

    # --- 2. hinku_list.csvから並び順を取得し、対象レコードのみを抽出 ---
    fiscal_year = compute_fiscal_year(target_month)
    hinku_path = os.path.join(master_dir, f'{fiscal_year}_hinku_list.csv')
    if not os.path.exists(hinku_path):
        print(f"【エラー】期{fiscal_year}: マスタファイルが見つかりません: {hinku_path}")
        return

    master_order = []
    seen = set() # 重複登録を防ぐためのセット

    for f_path in [hinku_path]:
        with open(f_path, 'r', encoding='cp932') as sf:
            reader = csv.reader(sf)
            next(reader, None) # 1行目（ヘッダー）をスキップ
            for row in reader:
                if len(row) >= 2:
                    k = row[0].strip()
                    h = row[1].strip()
                    
                    # 前提条件（N,G,K または特定のy）を満たすものだけを対象とする
                    if is_target_record(k, h):
                        if (k, h) not in seen:
                            seen.add((k, h))
                            master_order.append((k, h))

    if not master_order:
        print(f"【エラー】hinku_list.csv から抽出条件に合致するデータが見つかりませんでした。")
        return

    input_file = os.path.join(results_dir, args.data)
    output_file = os.path.join(results_dir, f"{month_str}_keiri_ratio.csv")

    if not os.path.exists(input_file):
        print(f"【エラー】入力ファイル '{input_file}' が見つかりません。")
        return

    # --- 3. データの集計 ---
    agg_data = {}
    total_target_hours = 0.0

    with open(input_file, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        
        for row in reader:
            if not row or len(row) < 5: continue
            
            month = row[0].strip()
            kubun = row[2].strip()
            hinku = row[3].strip()
            
            if month != target_month: continue
            
            # 条件に合致し、hinku_list に存在する組み合わせのみを按分対象として集計
            if (kubun, hinku) not in seen:
                continue
            
            row_hours = 0.0
            for val in row[4:]:
                if val.strip():
                    try:
                        row_hours += float(val)
                    except ValueError:
                        pass
                        
            total_target_hours += row_hours
            key = (kubun, hinku)
            agg_data[key] = agg_data.get(key, 0.0) + row_hours

    if total_target_hours == 0:
        print(f"【警告】指定された月 ({target_month}) の対象工数が 0 です。（フォーマット自体は出力されます）")

    # --- 4. 書き出し ---
    with open(output_file, 'w', newline='', encoding='cp932') as f:
        writer = csv.writer(f)
        writer.writerow(['内外製区分', '品区コード', '工数(hour)', '比率'])
        
        # hinku_list の順番通りに、工数が0でも省略せず出力する
        for key in master_order:
            kubun, hinku = key
            hours = agg_data.get(key, 0.0)
            ratio = (hours / total_target_hours) if total_target_hours > 0 else 0.0
            
            # 読み替えず、そのまま出力する
            writer.writerow([
                kubun,
                hinku,
                round(hours, 2),
                f"{ratio:.6f}"
            ])

    print(f"完了: 経理用CSVを出力しました -> {output_file}")
    print(f" (総対象工数: {total_target_hours:.2f}h, 出力行数: {len(master_order)}行)")

if __name__ == "__main__":
    main()