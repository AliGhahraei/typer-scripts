#!/usr/bin/env python3
import sys
from functools import wraps
from typing import Callable, Protocol

from domestobot import CmdRunnerContext, RunnerGroup, RunningMode, title
from rich.console import Console
from typer import Exit
from typer.models import CommandFunctionType

console = Console()
err_console = Console(stderr=True)


def task_title[**P, R](message: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            title(message)
            return f(*args, **kwargs)

        return wrapper

    return decorator


def make_runner_callback_decorator(
    callback: Callable[..., Callable[[CommandFunctionType], CommandFunctionType]],
) -> Callable[..., Callable[[CommandFunctionType], CommandFunctionType]]:
    @wraps(callback)
    def runner_callback(
        *args: object, **kwargs: object
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        return callback(*args, **dict(cls=RunnerGroup) | kwargs)

    return runner_callback


def info(message: str) -> None:
    console.print(message, style="cyan")


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
            print(f"function:{f.__name__}")
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
