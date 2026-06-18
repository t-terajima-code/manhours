# -*- coding: utf-8 -*-
"""[非推奨] run_all.bat 生成は make_bat.py に統合されました。

生成元の分散による文字化け事故を防ぐため、本ファイルは make_bat.py へ
委譲するだけのラッパーになりました。バッチ本文の編集は make_bat.py で行います。

  python make_bat.py        # 4本すべて再生成(推奨)
  python make_run_all.py    # 互換: 内部で make_bat.py を呼ぶ
"""
import sys

import make_bat

if __name__ == "__main__":
    print("[情報] run_all.bat の生成は make_bat.py に統合されています。")
    print("[情報] make_bat.py を実行して全バッチを CP932+CRLF で再生成します。")
    make_bat.write_bats()
    sys.exit(0)
