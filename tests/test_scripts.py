#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import List, Union, Iterable
from unittest.mock import Mock, call, patch

from pytest import CaptureFixture, fixture, raises, mark, MonkeyPatch

from typer_scripts.scripts import (check_repos_clean, check_yadm_clean,
                                   fetch_repos, fetch_yadm)

DARWIN = 'Darwin'
LINUX = 'Linux'
UNKNOWN_OS = 'Unknown OS'


@fixture
def run():
    with patch('typer_scripts.scripts.run') as run_mock:
        yield run_mock


@fixture
def repo1() -> Path:
    return Path('~/repo1')


@fixture
def repos(repo1: Path) -> List[Path]:
    return [repo1, Path('~/repo2')]


@fixture
def clean_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b'')


@fixture
def unsaved_changes_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b'M  fake_file')


@fixture
def unpushed_commits_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b'a9a152e (HEAD -> main) Create fake '
                            b'commit')


@fixture
def set_repos_env(monkeypatch: MonkeyPatch, repos: List[Path]):
    monkeypatch.setenv('TYPER_SCRIPTS_REPOS',
                       ' '.join([str(repo) for repo in repos]))
    yield


def assert_stdout(message: str, out: str):
    assert message in out


def assert_repo_not_clean(repo: Path, out: str) -> None:
    assert_stdout(f"Repository in {repo.expanduser()} was not clean", out)


def assert_repos_not_clean(repos: Iterable[Path], out: str)\
        -> None:
    for repo in repos:
        assert_repo_not_clean(repo, out)


def assert_clean_message_shown(out: str) -> None:
    assert_stdout("Everything's clean!", out)


def assert_repos_fetched(repos: Iterable[Path], run: Mock) -> None:
    run.assert_has_calls([
        call(['git', '-C', repo.expanduser(), 'fetch']) for repo in repos
    ])


def get_command_prefix_for_unpushed_commits() -> List[str]:
    return ['log', '--branches', '--not', '--remotes', '--oneline']


def get_unpushed_commits_args(repo: Path) -> List[Union[str, Path]]:
    return ['git', '-C', repo.expanduser(),
            *get_command_prefix_for_unpushed_commits()]


def get_command_prefix_for_unsaved_changes() -> List[str]:
    return ['status', '--ignore-submodules', '--porcelain']


def get_unsaved_changes_args(repo: Path) -> List[Union[str, Path]]:
    return ['git', '-C', repo.expanduser(),
            *get_command_prefix_for_unsaved_changes()]


class TestFetchYadm:
    @staticmethod
    @mark.usefixtures('run')
    def test_fetch_shows_fetching_yadm_message(
            capsys: CaptureFixture[str]
    ) -> None:
        fetch_yadm()
        assert_stdout('Fetching yadm', capsys.readouterr().out)

    @staticmethod
    def test_fetch_runs_fetch(run: Mock) -> None:
        fetch_yadm()
        run.assert_called_once_with(['yadm', 'fetch'])


class TestCheckYadmClean:
    @staticmethod
    @mark.usefixtures('run')
    def test_check_shows_checking_yadm_message(
            capsys: CaptureFixture[str]
    ) -> None:
        check_yadm_clean()
        assert_stdout('Checking yadm', capsys.readouterr().out)

    @staticmethod
    def test_check_shows_not_clean_on_yadm_with_unsaved_changes(
            run: Mock, capsys: CaptureFixture[str],
            unsaved_changes_output: CompletedProcess[bytes]
    ) -> None:
        run.side_effect = [unsaved_changes_output]
        check_yadm_clean()
        run.assert_called_once_with(
            ['yadm', *get_command_prefix_for_unsaved_changes()],
            capture_output=True,
        )
        assert_stdout('Yadm was not clean', capsys.readouterr().out)

    @staticmethod
    def test_check_shows_not_clean_on_yadm_with_unpushed_commits(
        run: Mock, capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes]
    ) -> None:
        run.side_effect = [clean_output, unpushed_commits_output]
        check_yadm_clean()
        run.assert_has_calls([
            call(['yadm', *get_command_prefix_for_unsaved_changes()],
                 capture_output=True),
            call(['yadm', *get_command_prefix_for_unpushed_commits()],
                 capture_output=True),
        ])
        assert_stdout('Yadm was not clean', capsys.readouterr().out)

    @staticmethod
    def test_check_shows_clean_on_clean_yadm(
        run: Mock, capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [clean_output] * 2
        check_yadm_clean()
        run.assert_has_calls([
            call(['yadm', *get_command_prefix_for_unsaved_changes()],
                 capture_output=True),
            call(['yadm', *get_command_prefix_for_unpushed_commits()],
                 capture_output=True),
        ])
        assert_stdout('Yadm was clean!', capsys.readouterr().out)


class TestFetchRepos:
    @staticmethod
    @mark.usefixtures('run')
    def test_fetch_shows_fetching_repos_message(
            repos: List[Path], capsys: CaptureFixture[str],
    ) -> None:
        fetch_repos(repos)

        assert_stdout('Fetching repos', capsys.readouterr().out)

    @staticmethod
    def test_fetch_is_run_for_every_repo(run: Mock, repos: List[Path]) \
            -> None:
        fetch_repos(repos)

        assert_repos_fetched(repos, run)

    @staticmethod
    @mark.usefixtures('set_repos_env')
    def test_fetch_uses_env_as_default(run: Mock, repos: List[Path],
                                       monkeypatch: MonkeyPatch) \
            -> None:
        fetch_repos()

        assert_repos_fetched(repos, run)

    @staticmethod
    def test_fetch_exits_without_repos(run: Mock) -> None:
        message = ('Either the `repos` argument or the `TYPER_SCRIPTS_REPO` '
                   'env variable must be provided')
        with raises(SystemExit, match=message):
            fetch_repos()


class TestCheckReposClean:
    @staticmethod
    @mark.usefixtures('run')
    def test_check_says_checking_repos_with_no_repos(
        capsys: CaptureFixture[str],
    ) -> None:
        check_repos_clean([])
        assert_stdout('Checking git repos', capsys.readouterr().out)

    @staticmethod
    def test_check_says_no_repos_without_running_commands_with_no_repos(
        run: Mock, capsys: CaptureFixture[str],
    ) -> None:
        check_repos_clean([])
        assert_stdout("No repos to check", capsys.readouterr().out)
        run.assert_not_called()

    @staticmethod
    def test_check_says_clean_on_clean_repos(
        run: Mock, repos: List[Path], capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes]
    ) -> None:
        run.side_effect = [clean_output for _ in range(len(repos) * 2)]
        check_repos_clean(repos)
        for repo in repos:
            run.assert_has_calls([
                call(get_unsaved_changes_args(repo), capture_output=True),
                call(get_unpushed_commits_args(repo), capture_output=True),
            ])
        assert_clean_message_shown(capsys.readouterr().out)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unsaved_changes(
        run: Mock, repo1: Path, capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes]
    ) -> None:
        run.side_effect = [unsaved_changes_output]
        check_repos_clean([repo1])
        run.assert_called_once_with(
            get_unsaved_changes_args(repo1), capture_output=True,
        )
        assert_repo_not_clean(repo1, capsys.readouterr().out)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unpushed_commits(
        run: Mock, repo1: Path, capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [clean_output, unpushed_commits_output]
        check_repos_clean([repo1])
        run.assert_has_calls([
            call(get_unsaved_changes_args(repo1), capture_output=True),
            call(get_unpushed_commits_args(repo1), capture_output=True),
        ])
        assert_repo_not_clean(repo1, capsys.readouterr().out)

    @staticmethod
    def test_check_exits_with_not_a_repo_error_on_invalid_repo(
        run: Mock, repo1: Path,
    ) -> None:
        run.side_effect = CalledProcessError(128, 'command')
        with raises(SystemExit,
                    match=f'Not a git repository: {repo1.expanduser()}'):
            check_repos_clean([repo1])
        run.assert_called_once_with(
            get_unsaved_changes_args(repo1), capture_output=True,
        )

    @staticmethod
    def test_check_reraises_unhandled_error(run: Mock, repo1: Path) -> None:
        exception = CalledProcessError(1, 'command')
        run.side_effect = exception
        message = "Command 'command' returned non-zero exit status 1."
        with raises(CalledProcessError, match=message):
            check_repos_clean([repo1])
        run.assert_called_once_with(
            get_unsaved_changes_args(repo1), capture_output=True
        )

    @staticmethod
    @mark.usefixtures('set_repos_env')
    def test_check_uses_env_as_default(
        run: Mock, repos: List[Path], capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes]
    ) -> None:
        run.return_value = unsaved_changes_output

        check_repos_clean()

        assert_repos_not_clean(repos, capsys.readouterr().out)
