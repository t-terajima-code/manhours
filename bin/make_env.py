# -*- coding: utf-8 -*-
"""bin/env(環境設定ファイル)を CP932 で生成する対話/引数スクリプト。

【env の構造(8行・全行が非空であること)】
  1行目  プロジェクトルートの絶対パス  (例: C:\\Users\\t-ter\\data\\python\\manhours)
  2行目  bin   サブディレクトリ        (例: \\bin)    ※現状スクリプトからは未参照だが行は必須
  3行目  member サブディレクトリ        (例: \\member)  担当者工数CSV
  4行目  kintai サブディレクトリ        (例: \\kintai)  勤怠Excel
  5行目  list  サブディレクトリ         (例: \\list)    マスタCSV
  6行目  soneki サブディレクトリ        (例: \\soneki)  損益Excel(Stage2)
  7行目  results サブディレクトリ        (例: \\results) 出力CSV
  8行目  1人日の標準労働時間(時間)       (例: 7.5)       人月換算用

【重要】
  - 各スクリプトの parse_env_file は空行を除外してから行番号で参照するため、
    8行すべてを非空にしないと行ズレで誤動作する。本生成器は全行非空を保証する。
  - エンコードは CP932(Shift-JIS)。文字化け防止のため UTF-8 で保存しないこと。

使い方:
    cd bin
    python make_env.py                          # 対話入力(Enterで既定値採用)
    python make_env.py --root C:\\path\\to\\proj # 引数指定(未指定項目は既定値)
    python make_env.py --root ... --output env2 --no-check
"""
import argparse
import os
import sys

# env 8行の既定値(ラベル, 既定値, ディレクトリ検証対象か)
ENV_FIELDS = [
    ("root", "プロジェクトルート(絶対パス)", None, "dir"),   # 既定はカレントの親(bin の親)
    ("bin", "bin サブディレクトリ", "\\bin", "subdir"),
    ("member", "member サブディレクトリ", "\\member", "subdir"),
    ("kintai", "kintai サブディレクトリ", "\\kintai", "subdir"),
    ("list", "list サブディレクトリ", "\\list", "subdir"),
    ("soneki", "soneki サブディレクトリ", "\\soneki", "subdir"),
    ("results", "results サブディレクトリ", "\\results", "subdir"),
    ("standard_time", "1人日の標準労働時間(時間)", "7.5", "float"),
]


def default_root():
    """既定のプロジェクトルート(= bin の親ディレクトリ)を返す。"""
    return os.path.dirname(os.path.abspath(os.path.dirname(__file__) or "."))


def build_env_lines(values):
    """値の辞書から env の8行(リスト)を組み立てる。

    values: {"root":..,"bin":..,"member":..,"kintai":..,"list":..,
             "soneki":..,"results":..,"standard_time":..}
    全行を非空文字列にして返す。
    """
    lines = []
    for key, _label, default, _kind in ENV_FIELDS:
        v = values.get(key)
        if v is None or str(v).strip() == "":
            if key == "root":
                v = default_root()
            else:
                v = default
        lines.append(str(v).strip())
    return lines


def validate_env_lines(lines, check_dirs=True):
    """env 8行の妥当性を検証する。問題があれば文字列リストで返す(空なら正常)。"""
    errors = []
    if len(lines) != 8:
        errors.append(f"行数が {len(lines)} です。8行必要です。")
        return errors

    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            errors.append(f"{i}行目が空です。全行を非空にしてください。")

    # 8行目: 標準労働時間が数値か
    try:
        t = float(lines[7])
        if t <= 0:
            errors.append(f"8行目(標準労働時間)は正の数にしてください: {lines[7]}")
    except ValueError:
        errors.append(f"8行目(標準労働時間)が数値ではありません: {lines[7]}")

    # ルートディレクトリの存在確認
    if check_dirs:
        root = lines[0]
        if not os.path.isdir(root):
            errors.append(f"1行目(プロジェクトルート)が存在しません: {root}")
        else:
            # サブディレクトリ(2〜7行目)の存在を確認(警告レベルだがエラーとして集約)
            for idx in range(1, 7):
                sub = lines[idx].lstrip("\\/")
                path = os.path.join(root, sub)
                if not os.path.isdir(path):
                    errors.append(f"{idx + 1}行目のディレクトリが存在しません: {path}")
    return errors


def write_env_file(lines, output_path):
    """env 8行を CP932 + 改行で書き出す。"""
    content = "\n".join(lines) + "\n"
    with open(output_path, "w", encoding="cp932", newline="") as f:
        f.write(content)


def prompt_values():
    """対話入力で各項目を受け取る(Enterで既定値採用)。"""
    values = {}
    print("=" * 54)
    print("  env(環境設定ファイル)生成 - Enterで既定値を採用")
    print("=" * 54)
    for key, label, default, _kind in ENV_FIELDS:
        d = default_root() if key == "root" else default
        ans = input(f"{label} [{d}]: ").strip()
        values[key] = ans if ans else d
    return values


def collect_values_from_args(args):
    """引数から値を集める(未指定は build_env_lines 側で既定値)。"""
    values = {}
    for key, _label, _default, _kind in ENV_FIELDS:
        values[key] = getattr(args, key, None)
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="env(環境設定ファイル)を CP932 で生成する")
    parser.add_argument("--output", "-o", default="env",
                        help="出力先ファイル名(既定: env)")
    parser.add_argument("--root", help="プロジェクトルート(絶対パス)")
    parser.add_argument("--bin", dest="bin", help="bin サブディレクトリ(既定: \\bin)")
    parser.add_argument("--member", help="member サブディレクトリ(既定: \\member)")
    parser.add_argument("--kintai", help="kintai サブディレクトリ(既定: \\kintai)")
    parser.add_argument("--list", dest="list", help="list サブディレクトリ(既定: \\list)")
    parser.add_argument("--soneki", help="soneki サブディレクトリ(既定: \\soneki)")
    parser.add_argument("--results", help="results サブディレクトリ(既定: \\results)")
    parser.add_argument("--standard-time", dest="standard_time",
                        help="1人日の標準労働時間(既定: 7.5)")
    parser.add_argument("--no-check", action="store_true",
                        help="ディレクトリ存在チェックを行わない")
    parser.add_argument("--force", action="store_true",
                        help="既存ファイルを確認なしで上書きする")
    args = parser.parse_args(argv)

    # 引数がすべて未指定なら対話モード
    arg_keys = ["root", "bin", "member", "kintai", "list",
                "soneki", "results", "standard_time"]
    any_specified = any(getattr(args, k, None) for k in arg_keys)

    if any_specified:
        values = collect_values_from_args(args)
    else:
        values = prompt_values()

    lines = build_env_lines(values)

    # 妥当性検証
    errors = validate_env_lines(lines, check_dirs=not args.no_check)
    if errors:
        print("[検証エラー]")
        for e in errors:
            print(f"  - {e}")
        print("修正するか、ディレクトリ未作成なら --no-check を付けて再実行してください。")
        return 1

    # 上書き確認
    if os.path.exists(args.output) and not args.force:
        if sys.stdin and sys.stdin.isatty():
            ans = input(f"'{args.output}' は既に存在します。上書きしますか? [y/N]: ")
            if ans.strip().lower() not in ("y", "yes"):
                print("[中止] 上書きをキャンセルしました。")
                return 1
        else:
            print(f"[エラー] '{args.output}' が既に存在します。"
                  "上書きするには --force を付けてください。")
            return 1

    write_env_file(lines, args.output)
    print(f"生成完了: {args.output} (CP932, 8行)")
    for i, line in enumerate(lines, 1):
        print(f"  {i}: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
