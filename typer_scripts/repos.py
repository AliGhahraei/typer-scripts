#!/usr/bin/env python3
import os
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from sys import exit

from domestobot import get_commands_callbacks, dry_run_option  # pyright: ignore[reportAny]
from typer import Context, Argument, Exit

from typer_scripts.core import (
    error,
    info,
    run_mode_option,  # pyright: ignore[reportAny]
    task_title,
    warning,
    run,
    RunMode,
    dry_run_repr,
)
from typer_scripts.typer_tools import App

app = App()


@app.callback(invoke_without_command=True)
def repos(ctx: Context, dry_run: bool = dry_run_option) -> None:
    """Check if your repositories are up-to-date and clean"""
    if ctx.invoked_subcommand is None:
        for command in get_commands_callbacks(app).values():
            command(mode=RunMode.DRY_RUN if dry_run else RunMode.DEFAULT)
    elif dry_run:
        error("Cannot pass dry-run and a subcommand")
        raise Exit(1)


@app.command()
@task_title("Fetching dotfiles")
def fetch_dotfiles(mode: RunMode = run_mode_option) -> None:
    """Fetch new changes for dotfiles."""
    run([*_get_git_dotfiles_command(), "fetch"], mode)


@app.command()
@task_title("Checking dotfiles")
@dry_run_repr
def check_dotfiles_clean(mode: RunMode = run_mode_option) -> None:
    """Check if dotfiles have unpublished work."""
    command = _get_git_dotfiles_command()
    if _has_unsaved_changes(*command, mode=RunMode.DEFAULT) or _has_unpushed_commits(
        *command, mode=RunMode.DEFAULT
    ):
        warning("Dotfiles were not clean")
    else:
        info("Dotfiles were clean!")


@app.command()
@task_title("Fetching repos")
def fetch_repos(
    mode: RunMode = run_mode_option, repos: list[Path] | None = Argument(None)
) -> None:
    """Fetch new changes for repos."""
    sanitized_repos = sanitize_repos(repos)
    for repo in sanitized_repos:
        run(["git", "-C", repo, "fetch"], mode)


@app.command()
@task_title("Checking git repos")
@dry_run_repr
def check_repos_clean(
    mode: RunMode = run_mode_option, repos: list[Path] | None = Argument(None)
) -> None:
    """Check if repos have unpublished work."""
    sanitized_repos = sanitize_repos(repos)
    if dirty_repos := [
        repo for repo in sanitized_repos if is_tree_dirty(repo, RunMode.DEFAULT)
    ]:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")


def _get_git_dotfiles_command() -> list[str]:
    return ["git", f"--git-dir={os.getenv('DOTFILES_REPO')}"]


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


def is_tree_dirty(dir_: Path, mode: RunMode) -> bool:
    try:
        is_dirty = _has_unsaved_changes(
            "git", "-C", dir_, mode=mode
        ) or _has_unpushed_commits("git", "-C", dir_, mode=mode)
    except CalledProcessError as e:
        if e.returncode == 128:
            exit(f"Not a git repository: {dir_}")
        else:
            raise
    return is_dirty


def _has_unsaved_changes(*command_prefix: str | Path, mode: RunMode) -> bool:
    unsaved_changes = run(
        [*command_prefix, "status", "--ignore-submodules", "--porcelain"],
        RunMode.DEFAULT,
        capture_output=True,
    )
    return bool(_decode_stripped(unsaved_changes))


def _has_unpushed_commits(*command_prefix: str | Path, mode: RunMode) -> bool:
    unpushed_commits = run(
        [*command_prefix, "log", "--branches", "--not", "--remotes", "--oneline"],
        RunMode.DEFAULT,
        capture_output=True,
    )
    return bool(_decode_stripped(unpushed_commits))


def _decode_stripped(command_output: CompletedProcess[bytes]) -> str:
    return command_output.stdout.decode("utf-8").strip()
