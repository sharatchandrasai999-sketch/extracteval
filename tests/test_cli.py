"""Tests for CLI input handling."""
import argparse
import json
from pathlib import Path

import pytest

from extracteval import __version__
from extracteval.cli import cmd_compare, cmd_try, main


def _args(text):
    return argparse.Namespace(task="tasks/invoices.yaml", text=text,
                              provider="mock", model=None)


def test_try_warns_on_empty_text(capsys):
    cmd_try(_args(text=""))
    assert "warning: empty --text" in capsys.readouterr().err


def test_try_warns_on_whitespace_only(capsys):
    cmd_try(_args(text="   \n"))
    assert "warning: empty --text" in capsys.readouterr().err


def test_try_quiet_on_real_text(capsys):
    cmd_try(_args(text="INVOICE #42 for Acme, 3 Mar 2025, $99"))
    captured = capsys.readouterr()
    assert "warning" not in captured.err
    out = json.loads(captured.out)
    assert set(out) == {"invoice_number", "customer", "date", "total"}


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "extracteval" in out
    assert __version__ in out


def test_compare_prints_leaderboard(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    task_path = Path(__file__).resolve().parent.parent / "tasks" / "invoices.yaml"
    cmd_compare(argparse.Namespace(task=str(task_path), providers="mock"))
    out = capsys.readouterr().out
    assert "Leaderboard" in out
    assert "invoices" in out
