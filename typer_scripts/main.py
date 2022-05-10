#!/usr/bin/env python3
import typer
from domestobot import (get_app as get_domestobot_app, get_root_dir,
                        get_groups_callbacks, dry_run_option)

from typer_scripts.repos import app as repos_app
from typer_scripts.typer_tools import App

CONFIG_APPLY = 'config-apply'


def get_app(path: str) -> typer.Typer:
    return get_domestobot_app(get_root_dir() / f'{path}.toml')


app = App()
app.add_typer(get_app('maintenance'))
app.add_typer(repos_app)
app.add_typer(get_app('backup'))
app.add_typer(get_app(CONFIG_APPLY))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, dry_run: bool = dry_run_option):
    if ctx.invoked_subcommand is None:
        for group_name, callback in get_groups_callbacks(app, ctx).items():
            if group_name != CONFIG_APPLY:
                callback(dry_run)
