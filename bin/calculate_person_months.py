# -*- coding: utf-8 -*-
import argparse
import csv
import os
import statistics

def parse_env_file(env_file_path):
    """
    envファイルを読み込み、ディレクトリ構成を取得する
    1行目：ルート / 7行目：results
    """
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")
        
    with open(env_file_path, 'r', encoding='cp932') as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if len(lines) < 8:
        raise ValueError("envファイルの行数が不足しています。少なくとも8行必要です。")
        
    root_dir = lines[0]
    # 7行目(index 6)が results ディレクトリ
    results_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))
    return results_dir

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
    parser = argparse.ArgumentParser(description='人工数および個人比率の算出ツール（raw_data.csvベース）')
    parser.add_argument('--env', type=str, default='env')
    parser.add_argument('--month', type=str, required=True, help='対象の年月 (例: 202603)')
    parser.add_argument('--data', type=str, default='raw_data.csv', help='入力データファイル名')
    args = parser.parse_args()

    # 月のフォーマット統一
    target_month = args.month.replace('-', '/')
    if len(target_month) == 6 and target_month.isdigit():
        target_month = f"{target_month[:4]}/{target_month[4:]}"
    month_str = target_month.replace('/', '')

    # 1. ディレクトリの取得
    try:
        results_dir = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】{e}")
        return

    # 入力ファイルを raw_data.csv に変更
    input_file = os.path.join(results_dir, args.data)

    if not os.path.exists(input_file):
        print(f"\n【エラー】指定されたファイルが見つかりません。")
        print(f"  探しているパス: {os.path.abspath(input_file)}")
        return

    # --- 2. データの読み込みと価値稼働工数の抽出 ---
    with open(input_file, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print("【エラー】ファイルが空です。"); return
            
        # raw_data.csv のヘッダー: ['月', '案件（業務）名', '内外製区分', '品区コード', 担当者1, 担当者2...]
        assignees = [h.strip() for h in headers[4:] if h.strip()]
        rows = list(reader)

    overall_target_hours = 0.0
    person_target_totals = {p: 0.0 for p in assignees}
    target_items = []

    for row in rows:
        if len(row) < 4: continue
        
        month_val = row[0].strip()
        task = row[1].strip()
        naigai = row[2].strip()
        hinku = row[3].strip()

        if month_val != target_month:
            continue

        # 対象プロジェクト（価値稼働工数）だけに限定して集計
        if is_target_record(naigai, hinku):
            indiv_vals = {}
            row_total = 0.0
            for i, p in enumerate(assignees):
                try:
                    val = float(row[4+i])
                except ValueError:
                    val = 0.0
                
                indiv_vals[p] = val
                row_total += val
                person_target_totals[p] += val
                overall_target_hours += val
                
            target_items.append({
                'month_type': month_val,
                'task': task,
                'naigai': naigai,
                'hinku': hinku,
                'total_hours': row_total,
                'indiv_vals': indiv_vals
            })

    # --- 3. 対象担当者の絞り込みと、業務統計データの算出 ---
    # トータルの時間がゼロの人は出力対象から完全に除外する
    valid_assignees = [p for p in assignees if person_target_totals[p] > 0]
    valid_headcount = len(valid_assignees)

    stats_data = {}
    all_valid_hours = []

    for p in valid_assignees:
        # 工数が0より大きい業務のみを抽出
        p_hours = [item['indiv_vals'][p] for item in target_items if item['indiv_vals'][p] > 0]
        all_valid_hours.extend(p_hours)
        
        count = len(p_hours)
        avg_h = sum(p_hours) / count if count > 0 else 0.0
        max_h = max(p_hours) if count > 0 else 0.0
        min_h = min(p_hours) if count > 0 else 0.0
        # 業務数が2件以上の場合は標準偏差を計算（1件以下の場合は0.0）
        std_h = statistics.stdev(p_hours) if count > 1 else 0.0

        stats_data[p] = {
            'count': count,
            'avg': avg_h,
            'max': max_h,
            'min': min_h,
            'std_dev': std_h
        }

    # 全員分の統計値（5列目出力用）
    all_count = len(all_valid_hours)
    all_avg = sum(all_valid_hours) / all_count if all_count > 0 else 0.0
    all_max = max(all_valid_hours) if all_count > 0 else 0.0
    all_min = min(all_valid_hours) if all_count > 0 else 0.0
    all_std = statistics.stdev(all_valid_hours) if all_count > 1 else 0.0

    # --- 4. 人工数 (Person-Month) の計算と出力 ---
    out_file = os.path.join(results_dir, f"{month_str}_person_months.csv")
    
    # ヘッダーも有効担当者のみで作成
    out_header = ['月', '案件（業務）名', '内外製区分', '品区コード', '時間(hour)', '人工数/月']
    for p in valid_assignees: 
        out_header.append(f"{p}_比率")

    with open(out_file, 'w', newline='', encoding='cp932') as f:
        writer = csv.writer(f)
        writer.writerow(out_header)
        
        total_pm = 0.0
        sum_person_ratios = {p: 0.0 for p in valid_assignees}
        
        for item in target_items:
            # 全体の人工数は、プロジェクトの比率に有効人数を乗じて算出
            project_ratio = item['total_hours'] / overall_target_hours if overall_target_hours > 0 else 0.0
            pm = project_ratio * valid_headcount
            total_pm += pm
            
            row_out = [item['month_type'], item['task'], item['naigai'], item['hinku'], round(item['total_hours'], 4), round(pm, 4)]
            
            # 各有効担当者の比率
            for p in valid_assignees:
                base_p = person_target_totals[p]
                ratio_p = item['indiv_vals'][p] / base_p if base_p > 0 else 0.0
                sum_person_ratios[p] += ratio_p
                row_out.append(f"{ratio_p:.6f}")
                
            writer.writerow(row_out)
            
        # 確認用合計行の出力
        writer.writerow([])
        sum_row = ['[対象案件合計]', '（価値稼働工数ベース）', '', '', round(overall_target_hours, 4), round(total_pm, 4)]
        for p in valid_assignees: 
            sum_row.append(f"{sum_person_ratios[p]:.6f}")
        writer.writerow(sum_row)

        # --- 担当者別および全体の業務統計行を出力 ---
        writer.writerow([])
        writer.writerow(['[担当者別 業務統計]', '（工数>0の業務）', '', '', '[全員の合計/統計]', ''] + ['' for _ in valid_assignees])
        
        # 5列目（インデックス4）に全体統計を配置し、以降に個人の統計を配置
        row_count = ['担当業務数(件)', '', '', '', f"{all_count}", '']
        row_avg = ['平均時間(h)', '', '', '', f"{all_avg:.2f}", '']
        row_max = ['最大時間(h)', '', '', '', f"{all_max:.2f}", '']
        row_min = ['最小時間(h)', '', '', '', f"{all_min:.2f}", '']
        row_std = ['標準偏差(h)', '', '', '', f"{all_std:.2f}", '']
        
        for p in valid_assignees:
            row_count.append(f"{stats_data[p]['count']}")
            row_avg.append(f"{stats_data[p]['avg']:.2f}")
            row_max.append(f"{stats_data[p]['max']:.2f}")
            row_min.append(f"{stats_data[p]['min']:.2f}")
            row_std.append(f"{stats_data[p]['std_dev']:.2f}")
            
        writer.writerow(row_count)
        writer.writerow(row_avg)
        writer.writerow(row_max)
        writer.writerow(row_min)
        writer.writerow(row_std)
        
        # 参考情報の出力
        writer.writerow([])
        writer.writerow(['[参考情報]', f"価値稼働した人数(有効人数): {valid_headcount}名", f"全体価値稼働時間: {overall_target_hours:.2f}h"])

    print(f"\n計算完了: 人工数算出データを出力しました -> {out_file}")
    print(f" (出力対象人数: {valid_headcount}名, 全体価値稼働時間: {overall_target_hours:.2f}h)")
    print(f" (対象プロジェクト数: {len(target_items)}件, 総対象人工数: {total_pm:.2f}PM)")

if __name__ == "__main__":
    main()