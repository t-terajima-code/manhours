# manhoursプロジェクト テスト実行ガイド

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. テスト実行

#### 全テスト実行
```bash
pytest tests/ -v
```

または、Windowsバッチファイル：
```bash
run_tests.bat
```

#### カバレッジレポート付きテスト実行
```bash
pytest tests/ --cov=bin --cov-report=term-missing --cov-report=html -v
```

または、Windowsバッチファイル：
```bash
run_tests_coverage.bat
```

### 3. 特定テストの実行

```bash
# 特定のテストクラスのみ
pytest tests/test_aggregate_hours.py::TestExcelDateToMonth -v

# 特定のテストメソッドのみ
pytest tests/test_aggregate_hours.py::TestExcelDateToMonth::test_valid_excel_date -v

# キーワード検索
pytest tests/ -k "parse" -v
```

## テスト構造

```
tests/
├── conftest.py           # フィクスチャ定義（テスト用データ）
├── test_aggregate_hours.py # aggregate_hours.pyのテスト
├── test_allocate_costs.py   # allocate_costs.pyのテスト（未実装）
└── fixtures/             # テストデータ保存先（将来用）
```

## テスト内容

### test_aggregate_hours.py
- **TestExcelDateToMonth**: Excelシリアル値→年月変換テスト
  - 正常系、エッジケース、エラーケース
- **TestExtractPersonName**: ファイル名からの人名抽出テスト
  - 複数のプリフィックス形式に対応
- **TestParseEnvFile**: 環境設定ファイル解析テスト
- **TestIntegration**: 統合テスト（全フロー検証）

## カバレッジレポート

テスト実行後、`htmlcov/index.html`で詳細なカバレッジレポートが確認できます。

## テスト追加方法

新しいテストを追加する場合：

1. 対象スクリプトに対応するテストファイルを作成（例：`test_allocate_costs.py`）
2. テストクラスを定義し、テストメソッドを追加
3. `pytest tests/` で実行

### テストテンプレート

```python
import pytest
from bin.allocate_costs import calculate_costs

class TestCalculateCosts:
    def test_normal_case(self):
        """正常系テスト"""
        result = calculate_costs(100, 0.2)
        assert result == 20

    def test_edge_case(self):
        """エッジケーステスト"""
        result = calculate_costs(0, 0.2)
        assert result == 0

    def test_error_case(self):
        """エラーケーステスト"""
        with pytest.raises(ValueError):
            calculate_costs(-100, 0.2)
```

## トラブルシューティング

### ModuleNotFoundError: No module named 'bin'

対象スクリプトをモジュールとしてインポートするため、conftest.pyで`sys.path`を設定しています。
テストを実行する時は、プロジェクトルートディレクトリから実行してください。

```bash
cd c:\Users\t-ter\data\python\manhours
pytest tests/
```

### エンコーディングエラー

テストで使用するCSVファイルは`cp932`エンコーディング（Shift JIS）を使用しています。
これは、aggregate_hours.pyの実装に合わせています。

## 次のステップ

1. 残りのスクリプト（allocate_costs.py、allocate_actual_hours.pyなど）のテスト実装
2. テストカバレッジの80%以上を達成
3. CI/CDパイプラインへの統合
