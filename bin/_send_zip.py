# -*- coding: utf-8 -*-
import json, smtplib, ssl, sys
from email.message import EmailMessage
from pathlib import Path

SMTP_JSON = Path(r"C:\Users\t-ter\data\srij_events\config\smtp.json")
FILE_PATH = Path(r"C:\Users\t-ter\data\python\manhours_dist\manhours_dist_20260618.tar.gz.b64.txt")
TO        = "terajima@meiji-rubber.co.jp"
SUBJECT   = "工数集計システム 配布版 manhours_dist_20260618（base64テキスト）"
BODY      = """\
寺島様

お世話になっております。

工数集計・按分システムの配布版をお送りします。

Gmailのセキュリティ制限により、アーカイブをbase64テキスト形式で送付しています。
添付ファイル「manhours_dist_20260618.tar.gz.b64.txt」を以下の手順でデコードしてください。

【デコード手順（コマンドプロンプトで実行）】
  python -c "import base64; open('manhours_dist.tar.gz','wb').write(base64.b64decode(open('manhours_dist_20260618.tar.gz.b64.txt').read()))"

上記を実行すると同じフォルダに manhours_dist.tar.gz が作成されます。

【tar.gz展開方法】
  右クリック →「すべて展開」、または
  コマンドプロンプトで: tar -xzf manhours_dist.tar.gz

【更新内容】
  - Pythonスクリプト（bin/*.py）を最新版に差し替え（エラー修正）
  - ダッシュボード（dashboard/）を同梱
  - 操作マニュアルをHTML版（OPERATION_MANUAL.html）に更新

【展開後の作業】
  1. 任意のフォルダに展開してください。
  2. bin/ フォルダ内の *.bat.txt ファイルを *.bat にリネームしてください。
     （セキュリティ制限のため .bat.txt で梱包しています）
       run_process.bat.txt       → run_process.bat
       run_allocate_costs.bat.txt → run_allocate_costs.bat
       run_all.bat.txt            → run_all.bat
  3. bin/ フォルダ内に env（拡張子なし）ファイルを作成し、
     project.env.template を参考に各データフォルダのパスを設定してください。
  4. bin/run_process.bat を実行してください。

ご不明な点はお気軽にご連絡ください。
よろしくお願いいたします。
"""

def main():
    conf = json.loads(SMTP_JSON.read_text(encoding="utf-8"))
    user, password = conf["user"], conf["password"]

    msg = EmailMessage()
    msg["From"]    = user
    msg["To"]      = TO
    msg["Subject"] = SUBJECT
    msg.set_content(BODY)
    msg.add_attachment(FILE_PATH.read_text(encoding="ascii"),
                       subtype="plain",
                       filename="manhours_20260618.txt")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=60) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
        print(f"OK: 送信完了 → {TO}  ({FILE_PATH.name})")

if __name__ == "__main__":
    sys.exit(main())
