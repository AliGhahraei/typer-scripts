#!/usr/bin/env python3
import subprocess
import sys
from enum import Enum
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import Annotated, Callable, Protocol

from rich.console import Console
from typer import Exit, Option

console = Console()
err_console = Console(stderr=True)


class RunMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    DEFAULT = "DEFAULT"


DRY_RUN_HELP = "Print commands for every step instead of running them"
dry_run_option = Option(help=DRY_RUN_HELP, show_default=False)  # pyright: ignore[reportAny]
run_mode_option = Option(hidden=True)  # pyright: ignore[reportAny]


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
        dry_run_args = tuple(args)
        print(dry_run_args)
        return CompletedProcess(dry_run_args, 0, str(dry_run_args).encode())
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


class CoreException(Exception):
    def __init__(self, message: str):
        self.message: str = message
        super().__init__(message)


def catch_exceptions[**P](f: Callable[P, None]) -> Callable[P, None]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            f(*args, **kwargs)
        except Exit:
            raise
        except CoreException as e:
            print(e.message, file=sys.stderr)
        except Exception:
            print("Unhandled error, printing traceback:", file=sys.stderr)
            raise

    return wrapper
