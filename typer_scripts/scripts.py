#!/usr/bin/env python3
import os
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, run
from sys import exit
from typing import Union, List, Optional

from typer import Typer

from typer_scripts.core import info, task_title, warning

_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT = '->'

app = Typer()


@app.command()
@task_title('Fetching yadm')
def fetch_yadm() -> None:
    """Fetch new changes for yadm."""
    run(['yadm', 'fetch'])


@app.command()
@task_title('Checking yadm')
def check_yadm_clean() -> None:
    """Check if yadm has unpublished work."""
    if (_has_unsaved_changes('yadm')
            or _has_unpushed_commits('yadm')):
        warning('Yadm was not clean')
    else:
        info('Yadm was clean!')


@app.command()
@task_title('Fetching repos')
def fetch_repos(repos: Optional[List[Path]] = None) \
        -> None:
    """Fetch new changes for repos."""
    sanitized_repos = sanitize_repos(repos)
    for repo in sanitized_repos:
        run(['git', '-C', repo, 'fetch'])


@app.command()
@task_title('Checking git repos')
def check_repos_clean(repos: Optional[List[Path]] = None) -> None:
    """Check if repos have unpublished work."""
    sanitized_repos = sanitize_repos(repos)
    if not sanitized_repos:
        info('No repos to check')
    elif dirty_repos := [repo for repo in sanitized_repos
                         if is_tree_dirty(repo)]:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")


def sanitize_repos(repos_param: Optional[List[Path]]) -> List[Path]:
    user_repos: List[Path] = (repos_param if repos_param is not None
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


def is_tree_dirty(dir_: Path) -> bool:
    try:
        is_dirty = (_has_unsaved_changes('git', '-C', dir_)
                    or _has_unpushed_commits('git', '-C', dir_))
    except CalledProcessError as e:
        if e.returncode == 128:
            exit(f'Not a git repository: {dir_}')
        else:
            raise
    return is_dirty


def _has_unsaved_changes(*command_prefix: Union[str, Path]) \
        -> bool:
    unsaved_changes = run(
        [*command_prefix, 'status', '--ignore-submodules', '--porcelain'],
        capture_output=True,
    )
    return bool(_decode(unsaved_changes))


def _has_unpushed_commits(*command_prefix: Union[str, Path]) \
        -> bool:
    unpushed_commits = run(
        [*command_prefix, 'log', '--branches', '--not', '--remotes',
         '--oneline'],
        capture_output=True,
    )
    return (_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT
            in _decode(unpushed_commits))


def _decode(command_output: CompletedProcess[bytes]) -> str:
    return command_output.stdout.decode('utf-8')
