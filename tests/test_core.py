#!/usr/bin/env python3
from unittest.mock import Mock

from pytest import raises
from typer import Exit

from typer_scripts.core import (
    CmdRunner,
    CmdRunnerContext,
    DefaultRunner,
    RunMode,
    err_console,
    set_runner_if_unset,
)


class TestDefaultRunner:
    @staticmethod
    def test_runner_executes_command() -> None:
        result = DefaultRunner()(["echo", "hi"], capture_output=True)
        assert "hi" in result.stdout.decode()


class TestSetObjIfUnset:
    @staticmethod
    def test_sets_obj_if_unset() -> None:
        ctx = Mock()
        ctx.obj = None
        set_runner_if_unset(ctx, True)
        assert ctx.obj  # pyright: ignore[reportAny]

    @staticmethod
    def test_does_not_set_obj_if_value_is_false() -> None:
        ctx = Mock()
        ctx.obj = True
        set_runner_if_unset(ctx, False)
        assert ctx.obj  # pyright: ignore[reportAny]

    @staticmethod
    def test_raise_exception_if_value_is_true_and_already_set() -> None:
        ctx = Mock()
        ctx.obj = True
        err_console.begin_capture()
        try:
            with raises(Exit):
                set_runner_if_unset(ctx, True)
        finally:
            assert "Cannot set dry-run more than once" in err_console.end_capture()


class TestCmdRunnerContext:
    @staticmethod
    def test_runner_runs_in_default_mode_by_default() -> None:
        default_runner = Mock(spec_set=CmdRunner)
        ctx = CmdRunnerContext(Mock(), default_runner=default_runner)

        _ = ctx(["a"])

        default_runner.assert_called_with(["a"], capture_output=False)
        assert ctx.mode == RunMode.DEFAULT

    @staticmethod
    def test_runner_runs_in_dry_run_mode() -> None:
        dry_runner = Mock(spec_set=CmdRunner)
        ctx = CmdRunnerContext(Mock(), dry_runner=dry_runner)

        dry_run = True
        ctx.obj = dry_run
        _ = ctx(["a"])

        dry_runner.assert_called_with(["a"], capture_output=False)
        assert ctx.mode == RunMode.DRY_RUN
