#!/usr/bin/env python3
import typer
from domestobot import (get_app as get_domestobot_app, get_root_dir,
                        get_groups_callbacks, dry_run_option)

from typer_scripts.repos import app as repos_app
from typer_scripts.typer_tools import Typer


def get_app(path: str) -> typer.Typer:
    return get_domestobot_app(get_root_dir() / f'{path}.toml')


app = Typer()
app.add_typer(get_app('maintenance'))
app.add_typer(repos_app)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, dry_run: bool = dry_run_option):
    if ctx.invoked_subcommand is None:
        for callback in get_groups_callbacks(app, ctx).values():
            callback(dry_run)
