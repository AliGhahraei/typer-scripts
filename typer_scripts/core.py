#!/usr/bin/env python3
import subprocess
from enum import Enum, auto
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, List, Union

from typer import style


class RunMode(Enum):
    DRY_RUN = auto()
    DEFAULT = auto()


def task_title(message: str) \
        -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:

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
        print(args)
        return CompletedProcess(args, 0, str(tuple(args)).encode())
    else:
        return subprocess.run(args, capture_output=capture_output)
