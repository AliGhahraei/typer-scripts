#!/usr/bin/env python3
from inspect import Parameter, signature
from functools import wraps
from typing import Callable, Any, Optional, cast

import typer
from typer.models import CommandFunctionType, Default


class Typer(typer.Typer):
    def callback(
            self,
            name: Optional[str] = Default(None),
            invoke_without_command: bool = Default(False),
            **kwargs: Any,
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            parent_callback = super(Typer, self).callback(
                name,
                invoke_without_command=invoke_without_command,
                **kwargs
            )
            wrapper = _fix_defaults(f)
            parent_callback(wrapper)
            return wrapper

        return decorator

    def command(
            self,
            name: Optional[str] = Default(None),
            **kwargs: Any,
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            parent_command = super(Typer, self).command(
                name,
                **kwargs
            )
            wrapper = _fix_defaults(f)
            parent_command(wrapper)
            return wrapper

        return decorator


def _fix_defaults(f: CommandFunctionType) -> CommandFunctionType:
    """https://github.com/tiangolo/typer/issues/279"""
    sig = signature(f)
    patched_defaults = {
        name: getattr(sig_default, 'default', sig_default)
        for name, sig_param in sig.parameters.items()
        if (sig_default := sig_param.default) is not Parameter.empty
    }

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        passed_args_names = {name for name, _
                             in zip(sig.parameters.keys(), args)}
        passed_params = passed_args_names | kwargs.keys()
        not_passed_params = sig.parameters.keys() - passed_params
        needed_defaults = {name: patched_defaults[name]
                           for name in not_passed_params}
        return f(*args, **kwargs, **needed_defaults)

    return cast(CommandFunctionType, wrapper)
