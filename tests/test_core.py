#!/usr/bin/env python3
from unittest.mock import Mock
from pytest import raises

from typer import Context, Exit

from typer_scripts.core import (
    CmdRunnerGetter,
    DefaultRunner,
    err_console,
    set_obj_if_unset,
)


class TestDefaultRunner:
    @staticmethod
    def test_runner_executes_command() -> None:
        result = DefaultRunner()(["echo", "hi"], capture_output=True)
        assert "hi" in result.stdout.decode()


class TestCmdRunnerParser:
    @staticmethod
    def test_convert_returns_default_runner_when_ctx_is_none() -> None:
        ctx = None
        default_runner = Mock()
        dry_runner = Mock()
        assert (
            CmdRunnerGetter(default_runner, dry_runner).convert("", None, ctx)
            == default_runner
        )

    @staticmethod
    def test_convert_returns_default_runner_when_ctx_obj_is_false() -> None:
        ctx = Mock(spec=Context)
        default_runner = Mock()
        dry_runner = Mock()
        ctx.obj = False
        assert (
            CmdRunnerGetter(default_runner, dry_runner).convert("", None, ctx)
            == default_runner
        )

    @staticmethod
    def test_convert_returns_dry_runner_when_ctx_obj_is_true() -> None:
        ctx = Mock(spec=Context)
        default_runner = Mock()
        dry_runner = Mock()
        ctx.obj = True
        assert (
            CmdRunnerGetter(default_runner, dry_runner).convert("", None, ctx)
            == dry_runner
        )


class TestSetObjIfUnset:
    @staticmethod
    def test_sets_obj_if_unset() -> None:
        ctx = Mock()
        ctx.obj = None
        set_obj_if_unset(ctx, True)
        assert ctx.obj  # pyright: ignore[reportAny]

    @staticmethod
    def test_does_not_set_obj_if_value_is_false() -> None:
        ctx = Mock()
        ctx.obj = True
        set_obj_if_unset(ctx, False)
        assert ctx.obj  # pyright: ignore[reportAny]

    @staticmethod
    def test_raise_exception_if_value_is_true_and_already_set() -> None:
        ctx = Mock()
        ctx.obj = True
        err_console.begin_capture()
        try:
            with raises(Exit):
                set_obj_if_unset(ctx, True)
        finally:
            assert "Cannot set dry-run more than once" in err_console.end_capture()
