#!/usr/bin/env python3
import subprocess
from enum import Enum
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, List, Union

from domestobot import dry_run_option
from typer import style

FunctionType = Callable[..., Any]


class RunMode(str, Enum):
    DRY_RUN = 'DRY_RUN'
    DEFAULT = 'DEFAULT'


def task_title(message: str) -> Callable[[FunctionType], FunctionType]:
    def decorator(f: FunctionType) -> FunctionType:

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            title(message)
            return f(*args, **kwargs)

        return wrapper
    return decorator


def title(message: str) -> None:
    dotted_message = f'\n{message}...'
    print(_colorize(dotted_message, 'magenta', bold=True))


def info(message: str) -> None:
    print(_colorize(message, 'cyan'))


def warning(message: str) -> None:
    print(_colorize(message, 'yellow'))


def _colorize(message: str, foreground: str, **kwargs: Any) -> str:
    return style(message, foreground, **kwargs)


def run(args: List[Union[str, Path]], mode: RunMode,
        capture_output: bool = False) -> CompletedProcess[bytes]:
    if mode is RunMode.DRY_RUN:
        dry_run_args = tuple(args)
        print(dry_run_args)
        return CompletedProcess(dry_run_args, 0, str(dry_run_args).encode())
    else:
        return subprocess.run(args, check=True, capture_output=capture_output)


def dry_run_repr(f: FunctionType) -> FunctionType:
    @wraps(f)
    def wrapper(*args: Any, mode: RunMode = dry_run_option, **kwargs: Any) \
            -> None:
        if mode is RunMode.DRY_RUN:
            print(f'function:{f.__name__}')
        else:
            f(*args, mode=mode, **kwargs)
    return wrapper
