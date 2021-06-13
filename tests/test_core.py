#!/usr/bin/env python3
from pytest import CaptureFixture

from typer_scripts.core import run, RunMode


class TestRun:
    @staticmethod
    def test_run_executes_command(capfd: CaptureFixture[str]):
        run(['echo', 'value'], RunMode.DEFAULT)

        assert 'value' in capfd.readouterr().out

    @staticmethod
    def test_run_captures_output(capfd: CaptureFixture[str]):
        result = run(['echo', 'value'], RunMode.DEFAULT,
                     capture_output=True)

        assert 'value' in result.stdout.decode()

    @staticmethod
    def test_run_prints_args_with_dry_run(capfd: CaptureFixture[str]):
        run(['echo', 'value'], RunMode.DRY_RUN)

        assert "('echo', 'value')" in capfd.readouterr().out

    @staticmethod
    def test_run_returns_expected_completed_process_with_dry_run():
        result = run(['echo', 'value'], RunMode.DRY_RUN)

        assert result.args == ('echo', 'value')
        assert result.returncode == 0
        assert result.stdout == b"('echo', 'value')"
