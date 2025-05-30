from unittest.mock import Mock

from domestobot import CmdRunnerContext, RunningMode

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

    @staticmethod
    def test_wrapped_is_not_called_when_ctx_obj_is_dry_run() -> None:
        wrapped_action = Mock()

        @dry_run_repr
        def f(cmd_runner: CmdRunnerContext) -> None:  # pyright: ignore[reportUnusedParameter]
            wrapped_action()

        ctx = CmdRunnerContext(Mock())
        ctx.obj = RunningMode.DRY_RUN

        f(ctx)

        wrapped_action.assert_not_called()
