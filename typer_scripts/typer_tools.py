#!/usr/bin/env python3
from typing import Callable, Any, cast, override

import typer
from typer.models import CommandFunctionType

from typer_scripts.core import catch_exceptions


class App(typer.Typer):
    @override
    def callback(
        self,
        **kwargs: Any,  # pyright: ignore[reportAny,reportExplicitAny]
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            parent_callback = super(App, self).callback(**kwargs)  # pyright: ignore[reportAny]
            wrapper = catch_exceptions(f)
            _ = parent_callback(wrapper)
            return cast(CommandFunctionType, wrapper)

        return decorator

    @override
    def command(
        self,
        name: str | None = None,
        **kwargs: Any,  # pyright: ignore[reportAny,reportExplicitAny]
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            parent_command = super(App, self).command(name, **kwargs)  # pyright: ignore[reportAny]
            wrapper = catch_exceptions(f)
            _ = parent_command(wrapper)
            return cast(CommandFunctionType, wrapper)

        return decorator
