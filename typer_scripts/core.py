#!/usr/bin/env python3
import subprocess
import sys
from enum import Enum
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import Annotated, Callable, Protocol, override

from click import ParamType, Parameter, Context as ClickContext
from rich.console import Console
from typer import Argument, Context, Exit, Option

console = Console()
err_console = Console(stderr=True)


class RunMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    DEFAULT = "DEFAULT"


DRY_RUN_HELP = "Print commands for every step instead of running them"
dry_run_option = Option(help=DRY_RUN_HELP, show_default=False)  # pyright: ignore[reportAny]
run_mode_option = Option(hidden=True)  # pyright: ignore[reportAny]


class CmdRunner(Protocol):
    def __call__(
        self, args: list[str | Path], capture_output: bool = False
    ) -> CompletedProcess[bytes]:  # pyright: ignore[reportReturnType]
        pass


def dry_runner(
    args: list[str | Path],
    capture_output: bool = False,  # pyright: ignore[reportUnusedParameter] to subclass CmdRunner
) -> CompletedProcess[bytes]:
    dry_run_args = tuple(args)
    print(dry_run_args)
    return CompletedProcess(dry_run_args, 0, str(dry_run_args).encode())


def default_runner(
    args: list[str | Path], capture_output: bool = False
) -> CompletedProcess[bytes]:
    return subprocess.run(args, check=True, capture_output=capture_output)


class CmdRunnerParser(ParamType):
    name: str = "CustomClass"

    def __init__(
        self,
        default_runner: CmdRunner = default_runner,
        dry_runner: CmdRunner = dry_runner,
    ) -> None:
        self.default_runner: CmdRunner = default_runner
        self.dry_runner: CmdRunner = dry_runner

    @override
    def convert(
        self, value: str, param: Parameter | None, ctx: ClickContext | None
    ) -> CmdRunner:
        return self.dry_runner if ctx and ctx.obj else self.default_runner  # pyright: ignore[reportAny]


new_run_mode_option = Argument(  # pyright: ignore[reportAny]
    hidden=True, click_type=CmdRunnerParser(), default_factory=lambda: ...
)


def set_obj_if_unset(ctx: Context, dry_run: bool) -> None:
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


def run(
    args: list[str | Path], mode: RunMode, capture_output: bool = False
) -> CompletedProcess[bytes]:
    if mode is RunMode.DRY_RUN:
        return dry_runner(args, capture_output)
    else:
        return subprocess.run(args, check=True, capture_output=capture_output)


class DryRunnable[**P](Protocol):
    __name__: str

    def __call__(self, mode: RunMode = ..., *args: P.args, **kwargs: P.kwargs) -> None:
        pass


def dry_run_repr[**P](f: DryRunnable[P]) -> DryRunnable[P]:
    @wraps(f)
    def wrapper(
        mode: Annotated[RunMode, run_mode_option] = RunMode.DEFAULT,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if mode is RunMode.DRY_RUN:
            print(f"function:{f.__name__}")  # type: ignore[attr-defined]
        else:
            f(mode, *args, **kwargs)

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
