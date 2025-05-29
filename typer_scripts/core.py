#!/usr/bin/env python3
import subprocess
import sys
from enum import Enum, auto
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, Protocol, override

from rich.console import Console
from typer import Context, Exit, Option
from typer.core import TyperCommand, TyperGroup
from typer.models import CommandFunctionType

console = Console()
err_console = Console(stderr=True)


DRY_RUN_HELP = "Print commands for every step instead of running them"
dry_run_option = Option(help=DRY_RUN_HELP, show_default=False)  # pyright: ignore[reportAny]


class RunningMode(str, Enum):
    DRY_RUN = auto()
    DEFAULT = auto()


class CmdRunner(Protocol):
    mode: RunningMode

    def __call__(
        self, args: list[str | Path], capture_output: bool = False
    ) -> CompletedProcess[bytes]:  # pyright: ignore[reportReturnType]
        pass


class CmdRunnerContext(Context, CmdRunner):
    mode: RunningMode = RunningMode.DEFAULT
    dry_runner: CmdRunner
    default_runner: CmdRunner

    def __init__(
        self,
        *args: object,
        dry_runner: CmdRunner | None = None,
        default_runner: CmdRunner | None = None,
        **kwargs: object,
    ) -> None:
        self.dry_runner = dry_runner or DryRunner()
        self.default_runner = default_runner or DefaultRunner()
        super().__init__(*args, **kwargs)  # pyright: ignore[reportArgumentType]

    @override
    def __call__(
        self, args: list[str | Path], capture_output: bool = False
    ) -> CompletedProcess[bytes]:
        dry_run: bool = bool(self.find_object(bool))
        self.mode = RunningMode.DRY_RUN if dry_run else RunningMode.DEFAULT
        runner = self.dry_runner if dry_run else self.default_runner
        return runner(args, capture_output=capture_output)


class RunnerGroup(TyperGroup):
    context_class: type[Context] = CmdRunnerContext  # pyright: ignore[reportIncompatibleVariableOverride] (invariant override)


class RunnerCommand(TyperCommand):
    context_class: type[Context] = CmdRunnerContext  # pyright: ignore[reportIncompatibleVariableOverride] (invariant override)


def make_runner_callback_decorator(
    callback: Callable[..., Callable[[CommandFunctionType], CommandFunctionType]],
) -> Callable[..., Callable[[CommandFunctionType], CommandFunctionType]]:
    @wraps(callback)
    def runner_callback(
        *args: object, **kwargs: object
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        return callback(*args, **dict(cls=RunnerGroup) | kwargs)

    return runner_callback


class DryRunner:
    mode: RunningMode

    def __init__(self) -> None:
        self.mode = RunningMode.DRY_RUN

    def __call__(
        self,
        args: list[str | Path],
        capture_output: bool = False,
    ) -> CompletedProcess[bytes]:
        dry_run_args = tuple(args)
        print(dry_run_args)
        return CompletedProcess(dry_run_args, 0, str(dry_run_args).encode())


class DefaultRunner:
    mode: RunningMode

    def __init__(self) -> None:
        self.mode = RunningMode.DEFAULT

    def __call__(
        self, args: list[str | Path], capture_output: bool = False
    ) -> CompletedProcess[bytes]:
        return subprocess.run(args, check=True, capture_output=capture_output)


def set_runner_if_unset(ctx: Context, dry_run: bool) -> None:
    if dry_run:
        if ctx.obj:  # pyright: ignore[reportAny]
            error("Cannot set dry-run more than once")
            raise Exit(1)
        ctx.obj = dry_run


def task_title[**P, R](message: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            title(message)
            return f(*args, **kwargs)

        return wrapper

    return decorator


def title(message: str) -> None:
    dotted_message = f"\n{message}..."
    console.print(dotted_message, style="bold magenta")


def info(message: str) -> None:
    console.print(message, style="cyan")


def warning(message: str) -> None:
    console.print(message, style="yellow")


def error(message: str) -> None:
    err_console.print(message, style="red")


class DryRunnable[**P](Protocol):
    __name__: str

    def __call__(
        self,
        cmd_runner: CmdRunnerContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        pass


def dry_run_repr[**P](f: DryRunnable[P]) -> DryRunnable[P]:
    @wraps(f)
    def wrapper(
        cmd_runner: CmdRunnerContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if cmd_runner.mode is RunningMode.DRY_RUN:
            print(f"function:{f.__name__}")  # type: ignore[attr-defined]
        else:
            f(cmd_runner, *args, **kwargs)

    return wrapper


def catch_exceptions[**P, R](f: Callable[P, R]) -> Callable[P, R]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return f(*args, **kwargs)
        except Exit:
            raise
        except Exception:
            print("Unhandled error, printing traceback:", file=sys.stderr)
            raise

    return wrapper
