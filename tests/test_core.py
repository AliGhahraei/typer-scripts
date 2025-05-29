#!/usr/bin/env python3
from unittest.mock import Mock

from pytest import fixture, raises
from typer import Context, Exit

from typer_scripts.core import (
    CmdRunner,
    CmdRunnerContext,
    DefaultRunner,
    RunningMode,
    err_console,
    set_obj_to_running_mode_if_unset,
)


class TestDefaultRunner:
    @staticmethod
    def test_runner_executes_command() -> None:
        result = DefaultRunner()(["echo", "hi"], capture_output=True)
        assert "hi" in result.stdout.decode()


class TestSetObjToRunningModeIfUnset:
    @fixture
    @staticmethod
    def ctx() -> Context:
        return Context(Mock())

    @staticmethod
    def test_sets_obj_if_unset(ctx: Context) -> None:
        ctx.obj = None
        set_obj_to_running_mode_if_unset(ctx, dry_run=True)
        assert ctx.obj is RunningMode.DRY_RUN  # pyright: ignore[reportAny]

    @staticmethod
    def test_does_not_set_obj_if_value_is_false(ctx: Context) -> None:
        ctx.obj = RunningMode.DEFAULT
        set_obj_to_running_mode_if_unset(ctx, dry_run=False)
        assert ctx.obj is RunningMode.DEFAULT  # pyright: ignore[reportAny]

    @staticmethod
    def test_raise_exception_if_value_is_true_and_already_set(ctx: Context) -> None:
        ctx.obj = RunningMode.DEFAULT
        err_console.begin_capture()
        try:
            with raises(Exit):
                set_obj_to_running_mode_if_unset(ctx, dry_run=True)
        finally:
            assert "Cannot set dry-run more than once" in err_console.end_capture()

    @staticmethod
    def test_sets_obj_if_value_is_true_and_already_set_to_different_type(
        ctx: Context,
    ) -> None:
        ctx.obj = "test_obj"
        set_obj_to_running_mode_if_unset(ctx, dry_run=True)
        assert ctx.obj is RunningMode.DRY_RUN  # pyright: ignore[reportAny]


class TestCmdRunnerContext:
    @staticmethod
    def test_runner_runs_in_default_mode_by_default() -> None:
        default_runner = Mock(spec_set=CmdRunner)
        ctx = CmdRunnerContext(Mock(), default_runner=default_runner)

        _ = ctx(["a"])

        default_runner.assert_called_with(["a"], capture_output=False)
        assert ctx.mode == RunningMode.DEFAULT

    @staticmethod
    def test_runner_runs_in_dry_run_mode() -> None:
        dry_runner = Mock(spec_set=CmdRunner)
        ctx = CmdRunnerContext(Mock(), dry_runner=dry_runner)

        ctx.obj = RunningMode.DRY_RUN
        _ = ctx(["a"])

        dry_runner.assert_called_with(["a"], capture_output=False)
        assert ctx.mode == RunningMode.DRY_RUN
