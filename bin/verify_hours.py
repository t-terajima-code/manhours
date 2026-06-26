# -*- coding: utf-8 -*-
import os
import glob
import csv
import re
import html
import argparse

def parse_env_file(env_file_path):
    """
    envファイルを読み込み、ディレクトリ構成を取得する
    1行目：ルート / 4行目：kintai / 7行目：results
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

    # 4行目が kintaiディレクトリ (勤怠データが置かれている)
    kintai_dir = os.path.join(root_dir, lines[3].lstrip('\\/'))
    
    # 7行目が resultsディレクトリ (raw_data.csvが置かれている)
    results_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))
    
    return root_dir, results_dir, kintai_dir

def parse_kintai_html(kintai_file_path):
    """
    HTML形式の勤怠データ(偽装XLS含む)から、名前、雇用区分、実働時間を抽出する
    """
    kintai_data = {}
    
    with open(kintai_file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()

    if '<html' in file_content.lower() or '<table' in file_content.lower():
        rows = re.findall(r'<tr.*?>(.*?)</tr>', file_content, re.IGNORECASE | re.DOTALL)
        name_idx = -1
        hours_idx = -1
        type_idx = -1
        
        for r in rows:
            cols_raw = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', r, re.IGNORECASE | re.DOTALL)
            cols = [html.unescape(re.sub(r'<.*?>', '', c)).strip().replace('\n', '').replace('\r', '') for c in cols_raw]
            
            if not cols: continue
                
            if name_idx == -1:
                if '名前' in cols and '実働時間' in cols:
                    name_idx = cols.index('名前')
                    hours_idx = cols.index('実働時間')
                    if '雇用区分' in cols:
                        type_idx = cols.index('雇用区分')
            else:
                if len(cols) > name_idx:
                    name_val = cols[name_idx].replace('\xa0', ' ').strip()
                    if name_val:
                        # 名前の表記揺れと先頭の社員番号等を除去
                        clean_name = re.sub(r'^[0-9]+', '', name_val).replace(' ', '').replace('　', '')
                        emp_type = cols[type_idx] if type_idx != -1 and len(cols) > type_idx else "不明"
                        
                        hours = 0.0
                        if len(cols) > hours_idx:
                            try:
                                hours = float(cols[hours_idx])
                            except ValueError:
                                pass
                                
                        kintai_data[clean_name] = {
                            'raw_name': name_val,
                            'type': emp_type,
                            'hours': hours
                        }
    return kintai_data

def main():
    # --- コマンドライン引数の設定 ---
    parser = argparse.ArgumentParser(description='勤怠データ ＆ 各担当者工数データ 検証ツール')
    parser.add_argument('--month', type=str, required=True, help='対象の年月 (例: 202603 または 2026/03)')
    parser.add_argument('--env', type=str, default='env', help='設定(env)ファイルのパス')
    parser.add_argument('--data', type=str, default='raw_data.csv', help='集計元のデータファイル名')
    parser.add_argument('--threshold', type=float, default=None, help='実働時間の許容不足割合(%%)。指定すると非対話式で実行 (例: 1.0)')
    args = parser.parse_args()

    # 月のフォーマット統一 (2026/03 形式と 202603 形式)
    target_month = args.month.replace('-', '/')
    if len(target_month) == 6 and target_month.isdigit():
        target_month = f"{target_month[:4]}/{target_month[4:]}"
    month_str = target_month.replace('/', '')

    print("="*60)
    print(f" 勤怠データ ＆ 各担当者工数データ 検証ツール [{month_str}版]")
    print("="*60)
    
    # 1. ディレクトリの解決
    try:
        root_dir, results_dir, kintai_dir = parse_env_file(args.env)
    except Exception as e:
        print(f"【エラー】設定ファイルの読み込みに失敗しました: {e}")
        return

    data_path = os.path.join(results_dir, args.data)
    if not os.path.exists(data_path):
        print(f"【エラー】入力データ '{data_path}' が見つかりません。")
        return

    # 2. 事前確認メッセージ
    print("【事前確認】")
    print("※ 勤怠データにはパートや派遣社員の方のデータは含まれていない想定です。")
    print("   含まれている場合は検証で不一致となる可能性がありますのでご注意ください。\n")
    
    # 3. 許容誤差(不足分)の入力（--threshold 引数で非対話式実行も可）
    if args.threshold is not None:
        threshold_percent = args.threshold
        print(f"[threshold] 許容割合: {threshold_percent}% (--threshold オプションより)")
    else:
        while True:
            try:
                threshold_str = input(">> 実働時間に満たない（不足している）許容割合(%)を入力してください (例: 1.0、完全に満たす必要がある場合は 0) : ")
                threshold_percent = float(threshold_str)
                if threshold_percent < 0:
                    print("※ 0以上の数値を入力してください。")
                    continue
                break
            except ValueError:
                print("※ 正しい数値を入力してください。")

    print("\n--- 検証を開始します ---")

    # 勤怠データ(*kintai*.xls)を探す
    kintai_search_pattern = os.path.join(kintai_dir, f'*{month_str}*kintai*.xls')
    kintai_files = glob.glob(kintai_search_pattern)
    
    if not kintai_files:
        print(f"エラー: {kintai_dir} 内に {month_str} を含む勤怠データ(*kintai*.xls)が見つかりません。")
        return
        
    kintai_path = kintai_files[0]
    kintai_data = parse_kintai_html(kintai_path)
    print(f"[OK] 勤怠データを読み込みました: {len(kintai_data)} 名分のデータを検出 ({os.path.basename(kintai_path)})")
    
    # --- 担当者の工数を raw_data.csv から集計 (制約条件あり) ---
    member_data = {}
    unregistered_tasks = {}  # {task_name: {assignee: hours}} マスタ未登録・区分未記入の業務
    with open(data_path, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            assignees = [h.strip() for h in headers[4:] if h.strip()]
        except StopIteration:
            print("【エラー】入力データが空です。")
            return

        # 担当者名キーを初期化（スペースを除去）
        for p in assignees:
            clean_p = p.replace(' ', '').replace('　', '')
            member_data[clean_p] = 0.0

        for row in reader:
            if len(row) < 5: continue

            month = row[0].strip()
            if month != target_month: continue

            task_name = row[1].strip()
            kubun = row[2].strip()
            hinku = row[3].strip()

            # 【重要】内外製区分と品区コードが両方とも空欄の行は、計算から除外する
            if not kubun and not hinku:
                # マスタ未登録・区分未記入として担当者別工数を記録
                for i, p_name in enumerate(assignees):
                    val = row[4+i].strip() if (4+i) < len(row) else ''
                    if val:
                        try:
                            h = float(val)
                            if h > 0:
                                if task_name not in unregistered_tasks:
                                    unregistered_tasks[task_name] = {}
                                unregistered_tasks[task_name][p_name] = unregistered_tasks[task_name].get(p_name, 0.0) + h
                        except ValueError:
                            pass
                continue

            # 対象行の場合、各担当者の工数を加算
            for i, p_name in enumerate(assignees):
                clean_p = p_name.replace(' ', '').replace('　', '')
                val = row[4+i].strip() if (4+i) < len(row) else ''
                if val:
                    try:
                        member_data[clean_p] += float(val)
                    except ValueError:
                        pass

    # 完全に0時間の人は member_data からも削除 (勤怠側の休職者対応と合わせる)
    member_data = {k: v for k, v in member_data.items() if v > 0}

    print(f"[OK] 担当者工数データ({args.data})を読み込み、制約条件を適用しました")

    # マスタ未登録・区分未記入の業務を担当者別に表示
    if unregistered_tasks:
        print("\n--- 【警告】マスタ未登録／区分未記入の業務（担当者別工数） ---")
        for task_name in sorted(unregistered_tasks.keys()):
            users = unregistered_tasks[task_name]
            user_list = ', '.join(f"{name}({h:.2f}h)" for name, h in sorted(users.items()))
            print(f"  - {task_name}: {user_list}")

    print("-" * 60)
    
    # 4. 人数とデータの突合検証・スキップ処理
    missing_in_kintai = []
    skipped_managers = []
    skipped_on_leave = []
    matched_names = []
    
    for k_name, k_info in kintai_data.items():
        # 休職者・休業者の判定・スキップ（実働時間が0の場合）
        if k_info['hours'] == 0.0:
            skipped_on_leave.append(k_info['raw_name'])
            continue
            
        # 勤怠データの名前が、工数データ名に含まれているかチェック
        matched = False
        for m_name in member_data.keys():
            if k_name in m_name or m_name in k_name:
                matched_names.append((k_name, m_name))
                matched = True
                break
                
        if not matched:
            # マッチしなかった場合、管理職ならスキップ、一般社員なら警告
            if '管理' in k_info['type'] or '監督' in k_info['type']:
                skipped_managers.append(k_info['raw_name'])
            else:
                print(f"【警告】勤怠に存在しますが、工数データがありません: {k_info['raw_name']} ({k_info['type']})")
            
    # 工数データ側をベースにチェック（勤怠にいない人）
    matched_m_names = [m for k, m in matched_names]
    for m_name in member_data.keys():
        if m_name not in matched_m_names:
            missing_in_kintai.append(m_name)
            
    for name in missing_in_kintai:
        print(f"【警告】工数データが存在しますが、勤怠データに名前がありません: {name}")
        
    # --- スキップした人物の一覧表示 ---
    if skipped_managers or skipped_on_leave:
        print("\n--- 検証から除外した対象者 ---")
        if skipped_managers:
            print(f"【マネージャー (データなし想定)】 計 {len(skipped_managers)} 名")
            for name in skipped_managers:
                print(f"  - {name}")
                
        if skipped_on_leave:
            print(f"【休職・休業者等 (実働0時間)】 計 {len(skipped_on_leave)} 名")
            for name in skipped_on_leave:
                print(f"  - {name}")

    print("\n--- 時間の検証結果 ---")
    
    # 5. 実働時間 vs 総工数の比較
    error_count = 0
    for k_name, m_name in matched_names:
        k_hours = kintai_data[k_name]['hours']
        m_hours = member_data[m_name]
        
        # 誤差の計算（工数 - 実働時間）
        # プラス(+)なら工数が多い、マイナス(-)なら工数が不足している
        diff = m_hours - k_hours
        error_ratio = (diff / k_hours * 100) if k_hours > 0 else 0.0
        
        # 誤差がマイナスであり、かつその不足割合が許容閾値を超えている場合のみ NG とする
        status_mark = "NG" if error_ratio < -threshold_percent else "OK"
        if status_mark == "NG":
            error_count += 1
            
        print(f"[{status_mark}] {kintai_data[k_name]['raw_name'][:12]:<12} | 勤怠: {k_hours:6.2f}h | 工数: {m_hours:6.2f}h | 誤差: {diff:+6.2f}h ({error_ratio:+6.2f}%)")

    print("-" * 60)
    if error_count == 0:
        print(f"[完了] 全員の工数が実働時間の許容基準を満たしています！")
    else:
        print(f"[警告] 実働時間に満たない（不足割合が {threshold_percent}% を超えている）担当者が {error_count} 名います。確認してください。")
        
    if args.threshold is None:
        input("\nEnterキーを押して終了します...")

if __name__ == "__main__":
    main()