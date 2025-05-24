#!/usr/bin/env python3
from typing import Callable, Any

import typer
from typer.models import CommandFunctionType, Default

from typer_scripts.core import catch_exceptions


class App(typer.Typer):
    def callback(
        self,
        *,
        invoke_without_command: bool = Default(False),
        **kwargs: Any,
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            parent_callback = super(App, self).callback(
                invoke_without_command=invoke_without_command, **kwargs
            )
            wrapper = catch_exceptions(f)
            parent_callback(wrapper)
            return wrapper

        return decorator

    def command(
        self,
        name: str | None = Default(None),
        **kwargs: Any,
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            parent_command = super(App, self).command(name, **kwargs)
            wrapper = catch_exceptions(f)
            parent_command(wrapper)
            return wrapper

        return decorator
