#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown から HTML への変換スクリプト
OPERATION_MANUAL.md を HTML に変換する
"""
import re
import os

def markdown_to_html(markdown_text):
    """Markdown テキストを HTML に変換"""

    html_lines = []

    # HTMLヘッダー
    html_lines.append('<!DOCTYPE html>')
    html_lines.append('<html lang="ja">')
    html_lines.append('<head>')
    html_lines.append('    <meta charset="utf-8">')
    html_lines.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_lines.append('    <title>工数集計・按分システム 集計担当向け作業マニュアル</title>')
    html_lines.append('    <style>')
    html_lines.append('''
        body {
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.8;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            font-size: 28px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            font-size: 22px;
        }
        h3 {
            color: #7f8c8d;
            margin-top: 20px;
            font-size: 18px;
        }
        h4 {
            color: #95a5a6;
            margin-top: 15px;
            font-size: 16px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: #f9f9f9;
        }
        table th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }
        table td {
            border: 1px solid #ddd;
            padding: 12px;
        }
        table tr:nth-child(even) {
            background-color: #f0f8ff;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Courier New", monospace;
            font-size: 14px;
        }
        pre {
            background-color: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            line-height: 1.5;
        }
        pre code {
            background-color: transparent;
            padding: 0;
            color: #abb2bf;
        }
        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 15px;
            color: #7f8c8d;
            font-style: italic;
            margin: 15px 0;
        }
        .note {
            background-color: #fffacd;
            border-left: 4px solid #ffb6c1;
            padding: 12px;
            margin: 15px 0;
        }
        .warning {
            background-color: #ffe4e1;
            border-left: 4px solid #ff6347;
            padding: 12px;
            margin: 15px 0;
        }
        .success {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 12px;
            margin: 15px 0;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        hr {
            border: none;
            height: 2px;
            background: linear-gradient(to right, transparent, #3498db, transparent);
            margin: 30px 0;
        }
        ul, ol {
            margin: 15px 0;
            padding-left: 30px;
        }
        li {
            margin: 8px 0;
        }
        strong {
            color: #2c3e50;
            font-weight: bold;
        }
        em {
            color: #7f8c8d;
        }
        .checkbox {
            margin-right: 8px;
        }
    ''')
    html_lines.append('    </style>')
    html_lines.append('</head>')
    html_lines.append('<body>')
    html_lines.append('    <div class="container">')

    # マークダウンの行を処理
    in_code_block = False
    in_table = False
    lines = markdown_text.split('\n')

    for i, line in enumerate(lines):
        # コードブロック処理
        if line.strip().startswith('```'):
            if in_code_block:
                html_lines.append('        </code>')
                html_lines.append('    </pre>')
                in_code_block = False
            else:
                html_lines.append('    <pre>')
                html_lines.append('        <code>')
                in_code_block = True
            continue

        if in_code_block:
            # HTMLエスケープ処理
            escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_lines.append('            ' + escaped_line)
            continue

        line_stripped = line.strip()

        # 空行処理
        if not line_stripped:
            if not in_table:
                html_lines.append('')
            continue

        # 見出し処理
        if line_stripped.startswith('# '):
            text = line_stripped[2:].strip()
            text = format_inline_text(text)
            html_lines.append(f'        <h1>{text}</h1>')
        elif line_stripped.startswith('## '):
            text = line_stripped[3:].strip()
            text = format_inline_text(text)
            html_lines.append(f'        <h2>{text}</h2>')
        elif line_stripped.startswith('### '):
            text = line_stripped[4:].strip()
            text = format_inline_text(text)
            html_lines.append(f'        <h3>{text}</h3>')
        elif line_stripped.startswith('#### '):
            text = line_stripped[5:].strip()
            text = format_inline_text(text)
            html_lines.append(f'        <h4>{text}</h4>')

        # 水平線処理
        elif line_stripped == '---':
            html_lines.append('        <hr>')

        # テーブル処理
        elif '|' in line_stripped:
            if not in_table:
                html_lines.append('        <table>')
                in_table = True

            cells = [cell.strip() for cell in line_stripped.split('|')[1:-1]]

            # ヘッダー判定（次行が区切り線か）
            is_header = False
            if i + 1 < len(lines) and all(c in '-|: ' for c in lines[i + 1]):
                is_header = True

            if is_header:
                html_lines.append('            <tr>')
                for cell in cells:
                    cell_text = format_inline_text(cell)
                    html_lines.append(f'                <th>{cell_text}</th>')
                html_lines.append('            </tr>')
            elif not all(c in '-|: ' for c in line_stripped):
                html_lines.append('            <tr>')
                for cell in cells:
                    cell_text = format_inline_text(cell)
                    html_lines.append(f'                <td>{cell_text}</td>')
                html_lines.append('            </tr>')

        elif in_table and '|' not in line_stripped:
            html_lines.append('        </table>')
            in_table = False

        # リスト処理
        elif line_stripped.startswith('- '):
            text = line_stripped[2:].strip()
            text = format_inline_text(text)
            html_lines.append(f'        <li>{text}</li>')

        elif line_stripped.startswith('□ '):
            text = line_stripped[2:].strip()
            text = format_inline_text(text)
            html_lines.append(f'        <li><span class="checkbox">☐</span>{text}</li>')

        # 段落処理
        else:
            text = format_inline_text(line_stripped)
            html_lines.append(f'        <p>{text}</p>')

    # テーブルの閉じ忘れチェック
    if in_table:
        html_lines.append('        </table>')

    html_lines.append('    </div>')
    html_lines.append('</body>')
    html_lines.append('</html>')

    return '\n'.join(html_lines)

def format_inline_text(text):
    """インラインテキストのフォーマット（太字、斜体など）"""
    # **太字** → <strong>太字</strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

    # *斜体* → <em>斜体</em>
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)

    # `code` → <code>code</code>
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # [link](url) → <a href="url">link</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    return text

def main():
    """メイン処理"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    input_file = os.path.join(project_dir, 'OPERATION_MANUAL.md')
    output_file = os.path.join(project_dir, 'OPERATION_MANUAL.html')

    # ファイル読み込み（UTF-8）
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
    except FileNotFoundError:
        return 1

    # HTML変換
    html_text = markdown_to_html(markdown_text)

    # ファイル出力（UTF-8）
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_text)
        return 0
    except Exception as e:
        return 1

if __name__ == '__main__':
    exit(main())
