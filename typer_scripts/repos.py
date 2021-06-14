#!/usr/bin/env python3
import os
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from sys import exit
from typing import Union, List, Optional

from domestobot import get_commands_callbacks, dry_run_option
from typer import Context, Option, Argument

from typer_scripts.core import (info, task_title, warning, run, RunMode,
                                dry_run_repr)
from typer_scripts.typer_tools import Typer

app = Typer()
run_mode_option = Option(RunMode.DEFAULT, hidden=True)


@app.callback(invoke_without_command=True)
def repos(ctx: Context, dry_run: bool = dry_run_option) -> None:
    """Check if your repositories are up-to-date and clean"""
    if ctx.invoked_subcommand is None:
        for command in get_commands_callbacks(app).values():
            command(mode=RunMode.DRY_RUN if dry_run else RunMode.DEFAULT)


@app.command()
@task_title('Fetching yadm')
def fetch_yadm(mode: RunMode = run_mode_option) -> None:
    """Fetch new changes for yadm."""
    run(['yadm', 'fetch'], mode)


@app.command()
@task_title('Checking yadm')
@dry_run_repr
def check_yadm_clean(mode: RunMode = run_mode_option) -> None:
    """Check if yadm has unpublished work."""
    if (_has_unsaved_changes('yadm', mode=RunMode.DEFAULT)
            or _has_unpushed_commits('yadm', mode=RunMode.DEFAULT)):
        warning('Yadm was not clean')
    else:
        info('Yadm was clean!')


@app.command()
@task_title('Fetching repos')
def fetch_repos(repos: Optional[List[Path]] = Argument(None),
                mode: RunMode = run_mode_option) \
        -> None:
    """Fetch new changes for repos."""
    sanitized_repos = sanitize_repos(repos)
    for repo in sanitized_repos:
        run(['git', '-C', repo, 'fetch'], mode)


@app.command()
@task_title('Checking git repos')
@dry_run_repr
def check_repos_clean(repos: Optional[List[Path]] = Argument(None),
                      mode: RunMode = run_mode_option) -> None:
    """Check if repos have unpublished work."""
    sanitized_repos = sanitize_repos(repos)
    if dirty_repos := [repo for repo in sanitized_repos
                       if is_tree_dirty(repo, RunMode.DEFAULT)]:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")


def sanitize_repos(repos_param: Optional[List[Path]]) -> List[Path]:
    user_repos: List[Path] = (repos_param if repos_param
                              else _read_repos_env())
    return [path.expanduser() for path in user_repos]


def _read_repos_env() -> List[Path]:
    try:
        env_repos = os.environ['TYPER_SCRIPTS_REPOS']
    except KeyError as e:
        message = ('Either the `repos` argument or the `TYPER_SCRIPTS_REPO` '
                   'env variable must be provided')
        raise SystemExit(message) from e
    return [Path(path) for path in env_repos.split(' ')]


def is_tree_dirty(dir_: Path, mode: RunMode) -> bool:
    try:
        is_dirty = (_has_unsaved_changes('git', '-C', dir_, mode=mode)
                    or _has_unpushed_commits('git', '-C', dir_, mode=mode))
    except CalledProcessError as e:
        if e.returncode == 128:
            exit(f'Not a git repository: {dir_}')
        else:
            raise
    return is_dirty


def _has_unsaved_changes(*command_prefix: Union[str, Path], mode: RunMode) \
        -> bool:
    unsaved_changes = run(
        [*command_prefix, 'status', '--ignore-submodules', '--porcelain'],
        RunMode.DEFAULT,
        capture_output=True,
    )
    return bool(_decode_stripped(unsaved_changes))


def _has_unpushed_commits(*command_prefix: Union[str, Path], mode: RunMode) \
        -> bool:
    unpushed_commits = run(
        [*command_prefix, 'log', '--branches', '--not', '--remotes',
         '--oneline'],
        RunMode.DEFAULT,
        capture_output=True,
    )
    return bool(_decode_stripped(unpushed_commits))


def _decode_stripped(command_output: CompletedProcess[bytes]) -> str:
    return command_output.stdout.decode('utf-8').strip()
