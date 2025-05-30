from unittest.mock import Mock

from _pytest.capture import CaptureFixture
from domestobot import CmdRunnerContext, RunningMode
from pytest import fixture

from typer_scripts.core import dry_run_repr


class TestDryRunRepr:
    @staticmethod
    def test_wrapped_is_called_by_default() -> None:
        @dry_run_repr
        def f(cmd_runner: CmdRunnerContext) -> None:
            _ = cmd_runner()

        runner = Mock()

        f(runner)

        runner.assert_called_with()

    class TestDryRunReprWithDryRunSet:
        @fixture
        @staticmethod
        def wrapped_action() -> Mock:
            return Mock()

        @fixture
        @staticmethod
        def ctx() -> CmdRunnerContext:
            ctx = CmdRunnerContext(Mock())
            ctx.obj = RunningMode.DRY_RUN
            return ctx

        @staticmethod
        def test_wrapped_is_dry_runned_for_no_args(
            capsys: CaptureFixture[str], wrapped_action: Mock, ctx: CmdRunnerContext
        ) -> None:
            @dry_run_repr
            def f(
                cmd_runner: CmdRunnerContext,
            ) -> None:
                wrapped_action(cmd_runner)

            f(ctx)

            assert "{f(cmd_runner)}" in capsys.readouterr().out
            wrapped_action.assert_not_called()

        @staticmethod
        def test_wrapped_is_dry_runned_for_pos_args(
            capsys: CaptureFixture[str], wrapped_action: Mock, ctx: CmdRunnerContext
        ) -> None:
            @dry_run_repr
            def f(
                cmd_runner: CmdRunnerContext,
                pos1: int,
                pos2: int,
            ) -> None:
                wrapped_action(cmd_runner, pos1, pos2)

            f(ctx, 1, 2)

            assert "{f(cmd_runner, 1, 2)}" in capsys.readouterr().out
            wrapped_action.assert_not_called()

        @staticmethod
        def test_wrapped_is_dry_runned_for_pos_args_and_kwargs(
            capsys: CaptureFixture[str], wrapped_action: Mock, ctx: CmdRunnerContext
        ) -> None:
            @dry_run_repr
            def f(
                cmd_runner: CmdRunnerContext,
                pos1: int,
                pos2: int,
                *,
                kwarg1: int,
                kwarg2: int,
            ) -> None:
                wrapped_action(cmd_runner, pos1, pos2, kwarg1, kwarg2)

            f(ctx, 1, 2, kwarg1=3, kwarg2=4)

            assert (
                "{f(cmd_runner, 1, 2, kwarg1=3, kwarg2=4)}" in capsys.readouterr().out
            )
            wrapped_action.assert_not_called()
