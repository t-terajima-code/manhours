# -*- coding: utf-8 -*-
import pytest
import os
import sys

# bin ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from make_env import (
    build_env_lines,
    validate_env_lines,
    write_env_file,
)
from aggregate_hours import parse_env_file


class TestBuildEnvLines:
    """build_env_lines() のテスト"""

    def test_full_values(self):
        """全項目指定で8行が組み立てられる"""
        values = {
            "root": r"C:\proj",
            "bin": r"\bin",
            "member": r"\member",
            "kintai": r"\kintai",
            "list": r"\list",
            "soneki": r"\soneki",
            "results": r"\results",
            "standard_time": "7.5",
        }
        lines = build_env_lines(values)
        assert lines == [
            r"C:\proj", r"\bin", r"\member", r"\kintai",
            r"\list", r"\soneki", r"\results", "7.5",
        ]

    def test_defaults_applied_for_missing(self):
        """未指定/空の項目には既定値が入り、全行が非空になる"""
        values = {"root": r"C:\proj"}  # 他は未指定
        lines = build_env_lines(values)
        assert len(lines) == 8
        assert all(l.strip() != "" for l in lines)
        # 既定値が採用されていること
        assert lines[2] == r"\member"
        assert lines[7] == "7.5"

    def test_empty_string_treated_as_default(self):
        """空文字も既定値に置換される"""
        values = {"root": r"C:\proj", "member": "   "}
        lines = build_env_lines(values)
        assert lines[2] == r"\member"


class TestValidateEnvLines:
    """validate_env_lines() のテスト"""

    def _valid_lines(self, root):
        return [
            root, r"\bin", r"\member", r"\kintai",
            r"\list", r"\soneki", r"\results", "7.5",
        ]

    def test_valid_with_real_dirs(self, temp_project_dir):
        """実在ルート + 既定ディレクトリで検証が通る(no-check)"""
        lines = self._valid_lines(temp_project_dir["root"])
        # ディレクトリチェック無しなら正常
        errors = validate_env_lines(lines, check_dirs=False)
        assert errors == []

    def test_wrong_line_count(self):
        """8行未満はエラー"""
        errors = validate_env_lines([r"C:\proj"], check_dirs=False)
        assert any("8行" in e for e in errors)

    def test_non_numeric_standard_time(self):
        """標準労働時間が非数値ならエラー"""
        lines = self._valid_lines(r"C:\proj")
        lines[7] = "abc"
        errors = validate_env_lines(lines, check_dirs=False)
        assert any("標準労働時間" in e for e in errors)

    def test_nonpositive_standard_time(self):
        """標準労働時間が0以下ならエラー"""
        lines = self._valid_lines(r"C:\proj")
        lines[7] = "0"
        errors = validate_env_lines(lines, check_dirs=False)
        assert any("標準労働時間" in e for e in errors)

    def test_empty_line_error(self):
        """空行があればエラー"""
        lines = self._valid_lines(r"C:\proj")
        lines[3] = ""
        errors = validate_env_lines(lines, check_dirs=False)
        assert any("空" in e for e in errors)

    def test_missing_root_dir(self):
        """check_dirs=True で存在しないルートはエラー"""
        lines = self._valid_lines(r"C:\definitely\nonexistent\xyz123")
        errors = validate_env_lines(lines, check_dirs=True)
        assert any("プロジェクトルート" in e for e in errors)


class TestWriteEnvFile:
    """write_env_file() のテスト"""

    def test_writes_cp932_and_parseable(self, temp_project_dir):
        """CP932 で書き出し、既存パーサで読めること"""
        root = temp_project_dir["root"]
        # parse_env_file 互換のため必要なサブディレクトリは temp_project_dir が用意済み
        lines = [
            root, r"\bin", r"\member", r"\kintai",
            r"\list", r"\soneki", r"\results", "7.5",
        ]
        env_path = os.path.join(root, "env")
        write_env_file(lines, env_path)

        # CP932 でデコードできること(文字化け防止)
        data = open(env_path, "rb").read()
        text = data.decode("cp932")  # 例外が出れば失敗
        non_empty = [l for l in text.splitlines() if l.strip()]
        assert len(non_empty) == 8

        # 既存パーサと互換であること
        staff, output, master = parse_env_file(env_path)
        assert staff == os.path.join(root, "member")
        assert output == os.path.join(root, "results")
        assert master == os.path.join(root, "list")

    def test_roundtrip_japanese_path(self, temp_project_dir):
        """日本語を含むパスでも CP932 で往復できる"""
        root = temp_project_dir["root"]
        lines = [
            root, r"\営業", r"\担当者", r"\勤怠",
            r"\一覧", r"\損益", r"\結果", "8.0",
        ]
        env_path = os.path.join(root, "env_jp")
        write_env_file(lines, env_path)
        text = open(env_path, "rb").read().decode("cp932")
        assert "\\担当者" in text
        assert "\\損益" in text
