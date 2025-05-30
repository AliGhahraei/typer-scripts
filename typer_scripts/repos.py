#!/usr/bin/env python3
import os
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from sys import exit
from typing import Annotated, Callable

from domestobot import (
    CmdRunner,
    CmdRunnerContext,
    RunnerCommand,
    dry_run_option,  # pyright: ignore[reportAny]
    get_commands_callbacks,
    set_obj_to_running_mode_if_unset,
    warning,
)
from typer.models import CommandFunctionType

from typer_scripts.core import (
    dry_run_repr,
    info,
    make_runner_callback_decorator,
    task_title,
)
from typer_scripts.typer_tools import App

app = App()


runner_callback = make_runner_callback_decorator(app.callback)


def runner_command(
    *args: object, **kwargs: object
) -> Callable[[CommandFunctionType], CommandFunctionType]:
    return app.command(*args, **dict(cls=RunnerCommand) | kwargs)  # pyright: ignore[reportArgumentType]


@runner_callback(invoke_without_command=True)
def repos(
    ctx: CmdRunnerContext, dry_run: Annotated[bool, dry_run_option] = False
) -> None:
    """Check if your repositories are up-to-date and clean"""
    set_obj_to_running_mode_if_unset(ctx, dry_run=dry_run)
    if ctx.invoked_subcommand is None:
        for command in get_commands_callbacks(app, ctx).values():
            command()


@runner_command()
@task_title("Fetching dotfiles")
def fetch_dotfiles(cmd_runner: CmdRunnerContext) -> None:
    """Fetch new changes for dotfiles."""
    _ = cmd_runner(*_get_git_dotfiles_command(), "fetch")


@runner_command()
@task_title("Checking dotfiles")
@dry_run_repr
def check_dotfiles_clean(
    cmd_runner: CmdRunnerContext,
) -> None:
    """Check if dotfiles have unpublished work."""
    command = *_get_git_dotfiles_command(), f"--work-tree={Path.home()}"
    if _has_unsaved_changes(cmd_runner, *command) or _has_unpushed_commits(
        cmd_runner, *command
    ):
        warning("Dotfiles were not clean")
    else:
        info("Dotfiles were clean!")


@runner_command()
@task_title("Fetching repos")
def fetch_repos(
    cmd_runner: CmdRunnerContext,
    repos: list[Path] | None = None,
) -> None:
    """Fetch new changes for repos."""
    sanitized_repos = sanitize_repos(repos)
    for repo in sanitized_repos:
        _ = cmd_runner("git", "-C", repo, "fetch")


@runner_command()
@task_title("Checking git repos")
@dry_run_repr
def check_repos_clean(
    cmd_runner: CmdRunnerContext,
    repos: list[Path] | None = None,
) -> None:
    """Check if repos have unpublished work."""
    sanitized_repos = sanitize_repos(repos)
    if dirty_repos := [
        repo for repo in sanitized_repos if is_tree_dirty(cmd_runner, repo)
    ]:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")


def _get_git_dotfiles_command() -> tuple[str, ...]:
    return "git", f"--git-dir={os.getenv('DOTFILES_REPO')}"


def sanitize_repos(repos_param: list[Path] | None) -> list[Path]:
    user_repos: list[Path] = repos_param if repos_param else _read_repos_env()
    return [path.expanduser() for path in user_repos]


def _read_repos_env() -> list[Path]:
    try:
        env_repos = os.environ["TYPER_SCRIPTS_REPOS"]
    except KeyError as e:
        message = (
            "Either the `repos` argument or the `TYPER_SCRIPTS_REPOS` "
            "env variable must be provided"
        )
        raise SystemExit(message) from e
    return [Path(path) for path in env_repos.split(" ")]


def is_tree_dirty(cmd_runner: CmdRunner, dir_: Path) -> bool:
    try:
        is_dirty = _has_unsaved_changes(
            cmd_runner,
            "git",
            "-C",
            dir_,
        ) or _has_unpushed_commits(cmd_runner, "git", "-C", dir_)
    except CalledProcessError as e:
        if e.returncode == 128:
            exit(f"Not a git repository: {dir_}")
        else:
            raise
    return is_dirty


def _has_unsaved_changes(runner: CmdRunner, *command_prefix: str | Path) -> bool:
    unsaved_changes = runner(
        *command_prefix,
        "status",
        "--ignore-submodules",
        "--porcelain",
        capture_output=True,
    )
    return bool(_decode_stripped(unsaved_changes))


def _has_unpushed_commits(runner: CmdRunner, *command_prefix: str | Path) -> bool:
    unpushed_commits = runner(
        *command_prefix,
        "log",
        "--branches",
        "--not",
        "--remotes",
        "--oneline",
        capture_output=True,
    )
    return bool(_decode_stripped(unpushed_commits))


def _decode_stripped(command_output: CompletedProcess[bytes]) -> str:
    return command_output.stdout.decode("utf-8").strip()
