# -*- coding: utf-8 -*-
import os
import glob
import pandas as pd

def parse_env_file(env_file_path):
    """
    envファイルを読み込み、ディレクトリパスを取得する
    1行目：ルート / 5行目：list / 7行目：results
    """
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"設定ファイル '{env_file_path}' が見つかりません。")

    with open(env_file_path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    if len(lines) < 7:
        raise ValueError("envファイルの行数が不足しています。少なくとも7行必要です。")

    root_dir = lines[0]
    list_dir = os.path.join(root_dir, lines[4].lstrip('\\/'))
    results_dir = os.path.join(root_dir, lines[6].lstrip('\\/'))
    test_dir = os.path.join(root_dir, 'test')

    return root_dir, list_dir, results_dir, test_dir

def load_and_merge(file_paths, df_hinku):
    """
    ファイルを読み込み、縦結合と横結合を行う
    """
    df_list = []
    for file in file_paths:
        df = pd.read_csv(file, encoding='cp932')
        df_list.append(df)

    if not df_list:
        return pd.DataFrame()

    df_all = pd.concat(df_list, ignore_index=True)

    df_merged = pd.merge(
        df_all,
        df_hinku,
        how='left',
        left_on=['内外製区分', '品区コード'],
        right_on=['naigaikubun', 'hinku']
    )

    df_merged.drop(columns=['naigaikubun', 'hinku'], inplace=True, errors='ignore')

    return df_merged

def main(env_file_path='env'):
    """
    メイン処理：データ読み込み、処理、出力
    """
    # 環境設定ファイル読み込み
    root_dir, list_dir, results_dir, test_dir = parse_env_file(env_file_path)

    # 出力先フォルダ作成
    os.makedirs(test_dir, exist_ok=True)

    # 品区リスト読み込み
    hinku_csv_path = os.path.join(list_dir, 'hinku_list.csv')
    df_hinku = pd.read_csv(hinku_csv_path, encoding='cp932')

    # 月次CSVファイル検索
    files_costs = glob.glob(os.path.join(results_dir, '*_allocated_costs.csv'))
    files_hours = glob.glob(os.path.join(results_dir, '*_allocated_hours.csv'))
    files_pm = glob.glob(os.path.join(results_dir, '*_person_months.csv'))

    # データ処理
    df_all_costs = load_and_merge(files_costs, df_hinku)
    df_all_hours = load_and_merge(files_hours, df_hinku)
    df_all_pm = load_and_merge(files_pm, df_hinku)

    # JSON変換
    json_costs = df_all_costs.to_json(orient='records', force_ascii=False) if not df_all_costs.empty else "[]"
    json_hours = df_all_hours.to_json(orient='records', force_ascii=False) if not df_all_hours.empty else "[]"
    json_pm = df_all_pm.to_json(orient='records', force_ascii=False) if not df_all_pm.empty else "[]"

    # JS出力
    js_output_path = os.path.join(test_dir, 'data.js')
    with open(js_output_path, 'w', encoding='utf-8') as f:
        f.write(f"const allCosts = {json_costs};\n\n")
        f.write(f"const allHours = {json_hours};\n\n")
        f.write(f"const allPersonMonths = {json_pm};\n")

    print(f"処理完了: data.js を {test_dir} に作成しました！")
    print(f"読み込み件数: 経費({len(files_costs)}件), 工数({len(files_hours)}件), 人工数({len(files_pm)}件)")

    return df_all_costs, df_all_hours, df_all_pm

if __name__ == '__main__':
    main()