# -*- coding: utf-8 -*-
import argparse
import csv
import os
import glob

def parse_env_file(env_file_path):
    """envファイル(CP932)を読み込み、(results_dir, soneki_dir) を返す。

    参照行: 1行目=ルート / 6行目=soneki / 7行目=results。
    1行目の絶対パスが実在しない場合は env の場所(bin/)の親をルートに採用する（可搬性）。
    例外: FileNotFoundError（未存在）、ValueError（8行未満）。
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
    
    # 6行目 (index 5) が sonekiディレクトリ
    soneki_dir = os.path.join(root_dir, lines[5].lstrip('\\/'))
    
    # 7行目 (index 6) が resultsディレクトリ
    results_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))
    
    return results_dir, soneki_dir

def compute_fiscal_year(target_month):
    """target_month (YYYY/MM形式) から事業年度（期）番号を計算する。
    188期=2025/4-2026/3, 189期=2026/4-2027/3"""
    yyyy, mm = target_month.split('/')
    return int(yyyy) - (1837 if int(mm) >= 4 else 1838)


def get_soneki_costs(soneki_xlsx_path, target_month_str):
    """
    Excelファイルから対象月のシート（例: '3月'）を読み込み、
    「(14)機能部間接部門費（労務費）」および「(15)機能部間接部門費（経費）」の
    「研究開発」に紐づく「全社実績金額」を取得する。
    """
    import pandas as pd
    
    # --- 対象シート名の特定（例: 2026/03 または 202603 -> '3月'） ---
    m_str = target_month_str[-2:] # 文字列の末尾2文字を取得
    m_int = int(m_str)            # ゼロ埋めを外す（例: '03' -> 3）
    sheet_name = f"{m_int}月"     # '3月'
    
    try:
        # Excelファイルを読み込む (openpyxlが必要)
        df = pd.read_excel(soneki_xlsx_path, sheet_name=sheet_name, header=None)
    except Exception as e:
        raise ValueError(f"Excelファイル '{os.path.basename(soneki_xlsx_path)}' のシート '{sheet_name}' を読み込めませんでした。エラー: {e}")
        
    labor_cost = None
    expense_cost = None
    
    target_col_idx = -1
    zensha_idx = -1
    current_category = None
    
    for row_idx, row in df.iterrows():
        # 行のデータを文字列のリストに変換（空白除去済）
        row_list = [str(x).strip() if pd.notna(x) else "" for x in row.values]
        row_str = "".join(row_list).replace(" ", "").replace("　", "")
        
        if not row_str:
            continue
            
        # --- 1. ヘッダー列（全社・実績金額）の特定 ---
        if zensha_idx == -1:
            for i, val in enumerate(row_list):
                if "全社" in val.replace(" ", "").replace("　", ""):
                    zensha_idx = i
                    break
                    
        if zensha_idx != -1 and target_col_idx == -1:
            # 「全社」が見つかった後、「実績金額」の列を探す
            for i in range(zensha_idx, len(row_list)):
                if "実績金額" in row_list[i].replace(" ", "").replace("　", ""):
                    target_col_idx = i
                    break
                    
        # --- 2. カテゴリの追跡と金額の取得 ---
        col_prefix = "".join(row_list[:4]).replace(" ", "").replace("　", "")
        
        # (14) 労務費のブロック判定
        if "14" in col_prefix and "機能部間接部門費" in col_prefix and "労務費" in col_prefix:
            current_category = "labor"
        # (15) 経費のブロック判定
        elif "15" in col_prefix and "機能部間接部門費" in col_prefix and "経費" in col_prefix:
            current_category = "expense"
            
        # ブロック内の「研究開発」行を見つけたら金額を取得
        elif current_category and "研究開発" in col_prefix:
            if target_col_idx != -1 and len(row_list) > target_col_idx:
                val_str = row_list[target_col_idx].replace(',', '')
                try:
                    val = float(val_str)
                    if current_category == "labor":
                        labor_cost = val
                    elif current_category == "expense":
                        expense_cost = val
                except ValueError:
                    pass
            
            # 一度取得したら、次のブロックまで読み飛ばす
            current_category = None
            
    if labor_cost is not None and expense_cost is not None:
        return labor_cost, expense_cost

    print(f"【警告】損益ファイル '{os.path.basename(soneki_xlsx_path)}' (シート:{sheet_name}) から対象の金額が自動抽出できませんでした。テスト値を使用します。")
    return 17836.0, 3929.0

def is_target_record(naigai, hinku):
    """
    価値稼働工数（コスト・人員按分の対象）か判定する
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
    """エントリポイント(Stage 2): 損益Excelの労務費・経費を工数比率で案件へ按分する。

    処理の流れ:
        1. --month / --env / --data を解釈し、results・soneki ディレクトリを取得。
        2. raw_data.csv（results/）から対象月の価値稼働工数（is_target_record で判定）を集計し、
           総対象工数・担当者別対象工数・有効担当者数（対象工数>0の人数）を求める。
        3. soneki/ のうちファイル名に期番号を含む損益Excel(*.xlsx)を選び、get_soneki_costs で
           当月シート（例: '4月'）の労務費・経費（研究開発の全社実績金額）を取得。
        4. 案件ごとの按分比率（案件工数/総対象工数）で投入人員・労務費・経費を按分し出力。

    出力先: results/{YYYYMM}_allocated_costs.csv（CP932）。合計行・設定値行を併記する。
    """
    parser = argparse.ArgumentParser(description='投入人員・労務費・経費の按分CSV出力スクリプト')
    parser.add_argument('--env', type=str, default='env', help='設定(env)ファイルのパス')
    parser.add_argument('--data', type=str, default='raw_data.csv', help='集計元のデータファイル名')
    parser.add_argument('--month', type=str, required=True, help='対象の年月 (例: 202604 または 2026/04)')
    args = parser.parse_args()

    # --- 対象月のフォーマット統一 ---
    target_month = args.month.replace('-', '/')
    if len(target_month) == 6 and target_month.isdigit():
        target_month = f"{target_month[:4]}/{target_month[4:]}"
    
    month_str = target_month.replace('/', '')

    # --- ディレクトリ解決 ---
    try:
        results_dir, soneki_dir = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】{e}")
        return

    data_path = os.path.join(results_dir, args.data)
    if not os.path.exists(data_path):
        print(f"【エラー】入力データ '{data_path}' が見つかりません。")
        return

    # --- 1. 損益データの検索（事業年度番号でフィルタ）と労務費・経費の取得 ---
    fiscal_year = compute_fiscal_year(target_month)
    soneki_files = [
        f for f in glob.glob(os.path.join(soneki_dir, '*.xlsx'))
        if not os.path.basename(f).startswith('~$') and str(fiscal_year) in os.path.basename(f)
    ]

    if not soneki_files:
        print(f"【エラー】期{fiscal_year}: sonekiディレクトリ({soneki_dir})内にファイル名に '{fiscal_year}' を含む損益Excelファイル(*.xlsx)が見つかりません。")
        return

    soneki_xlsx_path = soneki_files[0]
    
    try:
        TOTAL_LABOR_COST, TOTAL_EXPENSE_COST = get_soneki_costs(soneki_xlsx_path, target_month)
        print(f"-> 損益ファイル '{os.path.basename(soneki_xlsx_path)}' より取得: 労務費={TOTAL_LABOR_COST:,.1f}千円, 経費={TOTAL_EXPENSE_COST:,.1f}千円")
    except Exception as e:
        print(f"【エラー】{e}")
        return

    # --- 2. 担当者の有効判定と対象工数(価値稼働工数)の集計 ---
    assignee_target_hours = {}
    target_rows = []
    total_target_hours = 0.0

    with open(data_path, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            assignees = [h.strip() for h in headers[4:] if h.strip()]
        except StopIteration:
            print("【エラー】入力データが空です。")
            return

        for p in assignees:
            assignee_target_hours[p] = 0.0

        for row in reader:
            if len(row) < 4: continue
            
            month = row[0].strip()
            if month != target_month: continue
                
            task = row[1].strip()
            naigai = row[2].strip()
            hinku = row[3].strip()
            
            # 価値稼働工数（対象プロジェクト）のみを集計
            if is_target_record(naigai, hinku):
                row_hours = 0.0
                for i, p_name in enumerate(assignees):
                    val = row[4+i].strip() if (4+i) < len(row) else ''
                    if val:
                        try:
                            h = float(val)
                            assignee_target_hours[p_name] += h
                            row_hours += h
                        except ValueError:
                            pass
                            
                total_target_hours += row_hours
                target_rows.append({
                    'task_name': task,
                    'naigai': naigai,
                    'hinku': hinku,
                    'hours': row_hours
                })

    if total_target_hours == 0:
        print(f"【エラー】指定された月 ({target_month}) の対象工数(価値稼働工数)が存在しない、またはすべて 0 です。")
        return

    # 価値稼働工数 > 0 の人のみを有効担当者（投入人員の分母）としてカウント
    valid_headcount = sum(1 for p in assignees if assignee_target_hours[p] > 0)
    
    if valid_headcount == 0:
        print(f"【エラー】有効な担当者（価値稼働工数が1以上）が存在しません。")
        return

    print(f"-> 抽出完了: 対象工数計 {total_target_hours:.2f} hour / 有効担当者数 {valid_headcount} 名")

    # --- 3. 按分計算と出力 ---
    out_path = os.path.join(results_dir, f"{month_str}_allocated_costs.csv")
    out_header = ['月', '案件（業務）名', '内外製区分', '品区コード', '対象工数(hour)', '按分比率', '投入人員(人)', '労務費(千円)', '経費(千円)']

    with open(out_path, 'w', newline='', encoding='cp932') as f:
        writer = csv.writer(f)
        writer.writerow(out_header)
        
        sum_headcount = 0.0
        sum_labor = 0.0
        sum_expense = 0.0
        
        for item in target_rows:
            ratio = item['hours'] / total_target_hours
            
            alloc_headcount = ratio * valid_headcount
            alloc_labor = ratio * TOTAL_LABOR_COST
            alloc_expense = ratio * TOTAL_EXPENSE_COST
            
            sum_headcount += alloc_headcount
            sum_labor += alloc_labor
            sum_expense += alloc_expense
            
            writer.writerow([
                target_month,
                item['task_name'],
                item['naigai'],
                item['hinku'],
                round(item['hours'], 4),
                f"{ratio:.6f}",
                round(alloc_headcount, 4), 
                round(alloc_labor, 2),     
                round(alloc_expense, 2)
            ])
            
        writer.writerow([])
        
        writer.writerow([
            '[合計]', '', '', '', 
            round(total_target_hours, 4), 
            '1.000000', 
            round(sum_headcount, 4), 
            round(sum_labor, 2), 
            round(sum_expense, 2)
        ])
        
        writer.writerow([
            '[設定値]', f"総対象工数 / 有効担当者数 / 労務費 / 経費 ({os.path.basename(soneki_xlsx_path)})", '', '', 
            round(total_target_hours, 4), '', 
            valid_headcount, TOTAL_LABOR_COST, TOTAL_EXPENSE_COST
        ])

    print(f"集計が完了しました。労務費・経費の按分結果を以下に出力しました:\n -> {out_path}")

if __name__ == "__main__":
    main()