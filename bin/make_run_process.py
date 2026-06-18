# -*- coding: utf-8 -*-
"""[非推奨] run_process.bat 生成は make_bat.py に統合されました。

かつてこのファイルは run_process.bat の全文を独自に保持していましたが、
生成元が複数に分散し、実体 .bat と乖離して文字化け事故の原因になりました。
現在は make_bat.py を「唯一の正(source of truth)」とし、本ファイルは
互換のために make_bat.py へ委譲するだけのラッパーです。

  python make_bat.py          # 4本すべて再生成(推奨)
  python make_run_process.py  # 互換: 内部で make_bat.py を呼ぶ
"""
import sys

import make_bat

if __name__ == "__main__":
    print("[情報] run_process.bat の生成は make_bat.py に統合されています。")
    print("[情報] make_bat.py を実行して全バッチを CP932+CRLF で再生成します。")
    make_bat.write_bats()
    sys.exit(0)
