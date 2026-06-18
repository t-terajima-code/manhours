# -*- coding: utf-8 -*-
import argparse
import csv
import os
import glob
import re
import html

# 読み取り対象の休暇・欠勤等カラム名リスト
LEAVE_COLUMNS = [
    '有休', '特別有給休暇', '積立有休', '欠勤', '子の看護休暇', 
    '介護休暇', '公休', '産後パパ育休', '生理休暇', '組欠', 
    '無断欠勤', '公傷', '振替休日', '傷病休暇', '私用外出'
]

def compute_fiscal_year(target_month):
    """target_month (YYYY/MM形式) から事業年度（期）番号を計算する。
    188期=2025/4-2026/3, 189期=2026/4-2027/3"""
    yyyy, mm = target_month.split('/')
    return int(yyyy) - (1837 if int(mm) >= 4 else 1838)


def parse_env_file(env_file_path):
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")
        
    with open(env_file_path, 'r', encoding='cp932') as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if len(lines) < 8:
        raise ValueError("envファイルの行数が不足しています。少なくとも8行必要です。")
        
    root_dir = lines[0]
    kintai_dir = os.path.join(root_dir, lines[3].lstrip('\\/'))
    master_dir = os.path.join(root_dir, lines[4].lstrip('\\/'))
    results_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))
    
    try:
        standard_time = float(lines[7])
    except ValueError:
        standard_time = 7.5 # デフォルト値
    
    return results_dir, kintai_dir, master_dir, standard_time

def get_kintai_name(kintai_dict, m_name):
    clean_m = m_name.replace(' ', '').replace('　', '')
    if clean_m in kintai_dict:
        return clean_m
    for k in kintai_dict.keys():
        if k in clean_m or clean_m in k:
            return k
    return None

def parse_kintai_html(kintai_file_path):
    employee_work_hours = {}
    employee_leaves = {}
    
    with open(kintai_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    rows = re.findall(r'<tr.*?>(.*?)</tr>', content, re.IGNORECASE | re.DOTALL)
    
    name_idx = -1
    hours_idx = -1
    leave_indices = {}
    
    for r in rows:
        cols_raw = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', r, re.IGNORECASE | re.DOTALL)
        cols = [html.unescape(re.sub(r'<.*?>', '', c)).strip().replace('\n', '').replace('\r', '').replace('\xa0', ' ') for c in cols_raw]
        if not cols: continue

        if name_idx == -1:
            n_idx, h_idx = -1, -1
            for idx, c in enumerate(cols):
                if '名前' in c: n_idx = idx
                if '実働時間' in c: h_idx = idx
                
            if n_idx != -1 and h_idx != -1:
                name_idx = n_idx
                hours_idx = h_idx
                for idx, c in enumerate(cols):
                    for l_name in LEAVE_COLUMNS:
                        if l_name in c and l_name not in leave_indices:
                            leave_indices[l_name] = idx
            continue

        if len(cols) > max(name_idx, hours_idx):
            name_val = cols[name_idx].strip()
            if not name_val: continue
            
            clean_name = re.sub(r'^[0-9A-Za-z]+', '', name_val).replace(' ', '').replace('　', '')
            if not clean_name: continue
            
            try:
                val_str = re.sub(r'[^\d\.]', '', cols[hours_idx])
                work_h = float(val_str) if val_str else 0.0
            except ValueError:
                work_h = 0.0
                
            employee_work_hours[clean_name] = work_h
            
            leave_dict = {}
            for l_name, idx in leave_indices.items():
                if len(cols) > idx:
                    try:
                        val_str = re.sub(r'[^\d\.]', '', cols[idx])
                        leave_dict[l_name] = float(val_str) if val_str else 0.0
                    except ValueError:
                        leave_dict[l_name] = 0.0
                else:
                    leave_dict[l_name] = 0.0
            employee_leaves[clean_name] = leave_dict

    return employee_work_hours, employee_leaves

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', type=str, required=True, help='YYYYMM')
    parser.add_argument('--env', type=str, default='env')
    parser.add_argument('--data', type=str, default='raw_data.csv')
    args = parser.parse_args()

    target_month = args.month
    if len(target_month) == 6 and target_month.isdigit():
        target_month = f"{target_month[:4]}/{target_month[4:]}"
    month_str = target_month.replace('/', '')

    # 1. 環境設定の読み込み
    try:
        results_dir, kintai_dir, master_dir, standard_time = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】{e}"); return

    # 2. データの存在確認
    input_file = os.path.join(results_dir, args.data)
    if not os.path.exists(input_file):
        print(f"【エラー】{input_file} が見つかりません。"); return

    kintai_files = glob.glob(os.path.join(kintai_dir, f'*{month_str}*kintai*.xls'))
    if not kintai_files:
        print(f"【エラー】{kintai_dir} 内に {month_str} の勤怠データが見つかりません。"); return
    
    # 3. 勤怠データのパース
    emp_work_h, emp_leaves = parse_kintai_html(kintai_files[0])

    # 4. マスタデータの読み込み (nichijou_list.csvから「休暇」のコードを取得)
    fiscal_year = compute_fiscal_year(target_month)
    nichijou_path = os.path.join(master_dir, f'{fiscal_year}_nichijou_list.csv')
    if not os.path.exists(nichijou_path):
        print(f"【エラー】期{fiscal_year}: マスタファイルが見つかりません: {nichijou_path}")
        return

    nichijou_map = {}
    with open(nichijou_path, 'r', encoding='cp932') as sf:
        reader = csv.reader(sf)
        next(reader, None)
        for row in reader:
            if len(row) >= 3:
                nichijou_map[row[2].strip()] = (row[0].strip(), row[1].strip())
                    
    kyuka_naigai, kyuka_hinku = nichijou_map.get('休暇', ('', ''))

    # 5. raw_data.csv の読み込み
    all_rows = []
    with open(input_file, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        headers = next(reader)
        raw_assignees = [h.strip() for h in headers[4:]]
        for row in reader:
            if row[0] == target_month:
                all_rows.append(row)

    # raw_data.csv に名前がある担当者をすべて対象とする（kintai 不在者は休暇0として扱う）
    assignees = list(raw_assignees)

    if not assignees:
        print("【エラー】raw_data.csv に担当者が見つかりませんでした。")
        return

    # 6. 書き出し
    output_path = os.path.join(results_dir, f"{month_str}_allocated_hours.csv")
    with open(output_path, 'w', newline='', encoding='cp932') as f:
        writer = csv.writer(f)
        
        # ヘッダー (合計時間の列を追加)
        out_header = ['月', '案件（業務）名', '区分', '内外製区分', '品区コード', '合計時間(h)'] + assignees
        writer.writerow(out_header)

        # 各行（タスク）ごとの按分時間出力
        for row in all_rows:
            month_val = row[0]
            task_name = row[1]
            kubun = row[2]
            hinku = row[3]
            
            if not kubun and not hinku:
                continue
                
            out_row = [month_val, task_name, '実労働', kubun, hinku]
            
            allocated_h_list = []
            for i, p in enumerate(raw_assignees):
                if p in assignees:
                    try:
                        val = float(row[i+4])
                    except ValueError:
                        val = 0.0

                    allocated_h_list.append(round(val, 4))
            
            # 各担当者の按分時間を合算して「合計時間(h)」として追加
            total_h = sum(allocated_h_list)
            out_row.append(round(total_h, 4))
            
            # 各担当者の時間を追加
            out_row.extend(allocated_h_list)
                
            writer.writerow(out_row)

        # 休暇換算時間の出力
        writer.writerow([])
        writer.writerow(['', '[休暇・欠勤等換算]', '', '', '', ''] + ['' for _ in assignees])
        writer.writerow(['月', '種別', '区分', '内外製区分', '品区コード', '合計時間(h)'] + assignees)
        
        leave_row = [target_month, '休暇', '休暇等', kyuka_naigai, kyuka_hinku]
        has_leave = False
        
        p_leave_list = []
        for p in assignees:
            k_name = get_kintai_name(emp_leaves, p)
            p_leave_days = 0.0
            if k_name:
                for leave_name in LEAVE_COLUMNS:
                    p_leave_days += emp_leaves[k_name].get(leave_name, 0.0)
            
            if p_leave_days > 0:
                has_leave = True
            p_leave_list.append(round(p_leave_days * standard_time, 4))
            
        # 休暇の合計時間を計算して追加
        leave_total_h = sum(p_leave_list)
        leave_row.append(round(leave_total_h, 4))
        leave_row.extend(p_leave_list)
            
        if has_leave:
            writer.writerow(leave_row)

        # 新卒実習の読み込みと出力（期番号一致のみ）
        sinsotu_file = os.path.join(master_dir, f'{fiscal_year}_sinsotu.csv')
        sinsotu_path = [sinsotu_file] if os.path.exists(sinsotu_file) else []
        if sinsotu_path:
            writer.writerow([])
            writer.writerow(['', '[新卒工場実習]'])
            writer.writerow(['月', '項目', '区分', '内外製区分', '品区コード', '合計時間(h)', '人数', '稼働日数', '換算稼働時間(h)'])
            with open(sinsotu_path[0], 'r', encoding='cp932') as sf:
                s_reader = csv.reader(sf)
                for s_row in s_reader:
                    if s_row[0] == month_str:
                        try:
                            count = len(s_row) - 6
                            days = float(s_row[1])
                            total_h = days * float(s_row[2]) * count
                            writer.writerow([target_month, s_row[5], '新卒実習', s_row[3], s_row[4], round(total_h, 4), f"{count}名", f"{days}日", round(total_h, 4)])
                        except Exception:
                            pass

    print(f"按分完了: {output_path}")

if __name__ == "__main__":
    main()