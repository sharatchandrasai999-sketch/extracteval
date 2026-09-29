"""Tests for CLI input handling."""
import argparse
import json

from extracteval.cli import cmd_try


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
