#!/usr/bin/env python3
import subprocess
import sys
from enum import Enum
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, List, Union, TypeVar, cast

from domestobot import dry_run_option
from typer import style

ArgsType = TypeVar("ArgsType")
KwargsType = TypeVar("KwargsType")
ReturnType = TypeVar("ReturnType")
FunctionType = TypeVar("FunctionType", bound=Callable[..., Any])
StatementType = TypeVar("StatementType", bound=Callable[..., None])


class RunMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    DEFAULT = "DEFAULT"


def task_title(message: str) -> Callable[[FunctionType], FunctionType]:
    def decorator(f: FunctionType) -> FunctionType:
        @wraps(f)
        def wrapper(*args: ArgsType, **kwargs: KwargsType) -> ReturnType:
            title(message)
            return f(*args, **kwargs)

        return cast(FunctionType, wrapper)

    return decorator


def title(message: str) -> None:
    dotted_message = f"\n{message}..."
    print(_colorize(dotted_message, "magenta", bold=True))


def info(message: str) -> None:
    print(_colorize(message, "cyan"))


def warning(message: str) -> None:
    print(_colorize(message, "yellow"))


def _colorize(message: str, foreground: str, **kwargs: Any) -> str:
    return style(message, foreground, **kwargs)


def run(
    args: List[Union[str, Path]], mode: RunMode, capture_output: bool = False
) -> CompletedProcess[bytes]:
    if mode is RunMode.DRY_RUN:
        dry_run_args = tuple(args)
        print(dry_run_args)
        return CompletedProcess(dry_run_args, 0, str(dry_run_args).encode())
    else:
        return subprocess.run(args, check=True, capture_output=capture_output)


def dry_run_repr(f: StatementType) -> StatementType:
    @wraps(f)
    def wrapper(
        *args: ArgsType, mode: RunMode = dry_run_option, **kwargs: KwargsType
    ) -> None:
        if mode is RunMode.DRY_RUN:
            print(f"function:{f.__name__}")  # type: ignore[attr-defined]
        else:
            f(*args, mode=mode, **kwargs)

    return cast(StatementType, wrapper)


class CoreException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def catch_exceptions(f: StatementType) -> StatementType:
    @wraps(f)
    def wrapper(*args: ArgsType, **kwargs: KwargsType) -> None:
        try:
            f(*args, **kwargs)
        except CoreException as e:
            print(e.message, file=sys.stderr)
        except Exception:
            print("Unhandled error, printing traceback:", file=sys.stderr)
            raise

    return cast(StatementType, wrapper)
