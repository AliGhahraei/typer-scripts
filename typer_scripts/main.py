#!/usr/bin/env python3
import typer
from domestobot import (
    get_app,
    get_root_dir,
    get_groups_callbacks,
    dry_run_option,
)

from typer_scripts.repos import app as repos_app
from typer_scripts.typer_tools import App

CONFIG_APPLY = "config-apply"


def add_config_typer(app_: App, name: str) -> None:
    app_.add_typer(get_app(get_root_dir() / f"{name}.toml"), name=name)


app = App()
add_config_typer(app, "maintenance")
add_config_typer(app, "config-save")
app.add_typer(repos_app, name="repos")
add_config_typer(app, "backup")
add_config_typer(app, CONFIG_APPLY)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, dry_run: bool = dry_run_option):
    if ctx.invoked_subcommand is None:
        for group_name, callback in get_groups_callbacks(app, ctx).items():
            if group_name != CONFIG_APPLY:
                callback(dry_run)
