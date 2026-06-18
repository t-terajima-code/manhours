# -*- coding: utf-8 -*-
"""[非推奨] run_process.bat / run_all.bat 生成は make_bat.py に統合されました。

本ファイルはかつて run_process.bat と run_all.bat の全文を独自に保持して
いましたが、生成元の分散が文字化け事故の原因になったため廃止し、
make_bat.py へ委譲するだけのラッパーになりました。

  python make_bat.py    # 4本すべて再生成(推奨)
  python gen_bat.py     # 互換: 内部で make_bat.py を呼ぶ
"""
import sys

import make_bat

if __name__ == "__main__":
    print("[情報] バッチ生成は make_bat.py に統合されています。")
    print("[情報] make_bat.py を実行して全バッチを CP932+CRLF で再生成します。")
    make_bat.write_bats()
    sys.exit(0)
