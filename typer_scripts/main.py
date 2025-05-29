#!/usr/bin/env python3
from typing import Annotated

from domestobot import (
    get_app,
    get_groups_callbacks,
    get_root_dir,
)

from typer_scripts.core import (
    CmdRunnerContext,
    dry_run_option,  # pyright: ignore[reportAny]
    make_runner_callback_decorator,
    set_runner_if_unset,
)
from typer_scripts.repos import app as repos_app
from typer_scripts.typer_tools import App

CONFIG_APPLY = "config-apply"
REPOS = "repos"


def add_config_typer(app_: App, name: str) -> None:
    app_.add_typer(get_app(get_root_dir() / f"{name}.toml"), name=name)


app = App()
add_config_typer(app, "maintenance")
add_config_typer(app, "config-save")
app.add_typer(repos_app, name=REPOS)
add_config_typer(app, "backup")
add_config_typer(app, CONFIG_APPLY)


runner_callback = make_runner_callback_decorator(app.callback)


@runner_callback(invoke_without_command=True)
def main(ctx: CmdRunnerContext, dry_run: Annotated[bool, dry_run_option] = False):
    set_runner_if_unset(ctx, dry_run)
    if ctx.invoked_subcommand is None:
        for group_name, callback in get_groups_callbacks(app, ctx).items():
            if group_name == REPOS:
                callback()
            elif group_name != CONFIG_APPLY:
                callback(dry_run)
