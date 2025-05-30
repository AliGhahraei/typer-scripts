#!/usr/bin/env python3
from collections.abc import Iterable
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import Any
from unittest.mock import Mock, call

from domestobot import CmdRunnerContext
from pytest import CaptureFixture, MonkeyPatch, fixture, mark, raises
from typer.testing import CliRunner

from typer_scripts.repos import (
    app,
    check_dotfiles_clean,
    check_repos_clean,
    fetch_dotfiles,
    fetch_repos,
)

DARWIN = "Darwin"
LINUX = "Linux"
UNKNOWN_OS = "Unknown OS"


@fixture
def runner() -> Mock:
    runner = Mock(spec_set=CmdRunnerContext)
    return runner


@fixture
def repo1() -> Path:
    return Path("~/repo1")


@fixture
def repos(repo1: Path) -> list[Path]:
    return [repo1, Path("~/repo2")]


@fixture
def clean_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b"  ")


@fixture
def unsaved_changes_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b"M  fake_file")


@fixture
def unpushed_commits_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b"a9a152e (HEAD -> main) Create fake commit")


@fixture
def set_repos_env(monkeypatch: MonkeyPatch, repos: list[Path]):
    monkeypatch.setenv("TYPER_SCRIPTS_REPOS", " ".join([str(repo) for repo in repos]))
    yield


@fixture
def set_dotfiles_env(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("DOTFILES_REPO", "TEST_DOTFILES_REPO")


def assert_stdout(message: str, out: str):
    assert message in out


def assert_repo_not_clean(repo: Path, out: str) -> None:
    assert_stdout(f"Repository in {repo.expanduser()} was not clean", out)


def assert_repos_not_clean(repos: Iterable[Path], out: str) -> None:
    for repo in repos:
        assert_repo_not_clean(repo, out)


def assert_clean_message_shown(out: str) -> None:
    assert_stdout("Everything's clean!", out)


def assert_repos_fetched(repos: Iterable[Path], runner: Mock) -> None:
    runner.assert_has_calls([call(*get_git_fetch_args(repo)) for repo in repos])


def get_dotfiles_clean_prefix() -> tuple[str, ...]:
    return *get_dotfiles_prefix(), f"--work-tree={Path.home()}"


def get_dotfiles_prefix() -> tuple[str, ...]:
    return "git", "--git-dir=TEST_DOTFILES_REPO"


def get_fetch_dotfiles_args() -> tuple[str, ...]:
    return *get_dotfiles_prefix(), "fetch"


def get_git_fetch_args(repo: Path) -> tuple[str | Path, ...]:
    return "git", "-C", repo.expanduser(), "fetch"


def get_command_prefix_for_unpushed_commits() -> tuple[str, ...]:
    return "log", "--branches", "--not", "--remotes", "--oneline"


def get_unpushed_commits_args(repo: Path) -> tuple[str | Path, ...]:
    return "git", "-C", repo.expanduser(), *get_command_prefix_for_unpushed_commits()


def get_command_prefix_for_unsaved_changes() -> tuple[str, ...]:
    return "status", "--ignore-submodules", "--porcelain"


def get_unsaved_changes_args(repo: Path) -> tuple[str | Path, ...]:
    return "git", "-C", repo.expanduser(), *get_command_prefix_for_unsaved_changes()


class TestFetchDotfiles:
    @staticmethod
    def test_fetch_shows_fetching_dotfiles_message(
        runner: Mock, capsys: CaptureFixture[str]
    ) -> None:
        fetch_dotfiles(runner)

        assert_stdout("Fetching dotfiles", capsys.readouterr().out)

    @staticmethod
    @mark.usefixtures("set_dotfiles_env")
    def test_fetch_runs_fetch(runner: Mock) -> None:
        fetch_dotfiles(runner)

        runner.assert_called_once_with(*get_fetch_dotfiles_args())


@mark.usefixtures("set_dotfiles_env")
class TestCheckDotfilesClean:
    @staticmethod
    def test_check_shows_checking_dotfiles_message(
        runner: Mock, capsys: CaptureFixture[str]
    ) -> None:
        check_dotfiles_clean(runner)

        assert_stdout("Checking dotfiles", capsys.readouterr().out)

    @staticmethod
    def test_check_shows_not_clean_on_dotfiles_with_unsaved_changes(
        runner: Mock,
        capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes],
    ) -> None:
        runner.side_effect = [unsaved_changes_output]

        check_dotfiles_clean(runner)

        runner.assert_called_once_with(
            *get_dotfiles_clean_prefix(),
            *get_command_prefix_for_unsaved_changes(),
            capture_output=True,
        )
        assert_stdout("Dotfiles were not clean", capsys.readouterr().err)

    @staticmethod
    def test_check_shows_not_clean_on_dotfiles_with_unpushed_commits(
        runner: Mock,
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes],
    ) -> None:
        runner.side_effect = [clean_output, unpushed_commits_output]

        check_dotfiles_clean(runner)

        runner.assert_has_calls(
            [
                call(
                    *get_dotfiles_clean_prefix(),
                    *get_command_prefix_for_unsaved_changes(),
                    capture_output=True,
                ),
                call(
                    *get_dotfiles_clean_prefix(),
                    *get_command_prefix_for_unpushed_commits(),
                    capture_output=True,
                ),
            ]
        )
        assert_stdout("Dotfiles were not clean", capsys.readouterr().err)

    @staticmethod
    def test_check_shows_clean_on_clean_dotfiles(
        runner: Mock,
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
    ) -> None:
        runner.side_effect = [clean_output] * 2

        check_dotfiles_clean(runner)

        runner.assert_has_calls(
            [
                call(
                    *get_dotfiles_clean_prefix(),
                    *get_command_prefix_for_unsaved_changes(),
                    capture_output=True,
                ),
                call(
                    *get_dotfiles_clean_prefix(),
                    *get_command_prefix_for_unpushed_commits(),
                    capture_output=True,
                ),
            ]
        )
        assert_stdout("Dotfiles were clean!", capsys.readouterr().out)


class TestFetchRepos:
    @staticmethod
    def test_fetch_shows_fetching_repos_message(
        runner: Mock,
        repos: list[Path],
        capsys: CaptureFixture[str],
    ) -> None:
        fetch_repos(runner, repos=repos)

        assert_stdout("Fetching repos", capsys.readouterr().out)

    @staticmethod
    def test_fetch_is_run_for_every_repo(runner: Mock, repos: list[Path]) -> None:
        fetch_repos(runner, repos=repos)

        assert_repos_fetched(repos, runner)

    @staticmethod
    @mark.usefixtures("set_repos_env")
    def test_fetch_uses_env_as_default(runner: Mock, repos: list[Path]) -> None:
        fetch_repos(runner)

        assert_repos_fetched(repos, runner)

    @staticmethod
    @mark.parametrize("kwargs", [{}, {"repos": None}, {"repos": list[Path]()}])
    def test_fetch_exits_without_repos(
        runner: Mock,
        kwargs: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    ) -> None:
        message = (
            "Either the `repos` argument or the `TYPER_SCRIPTS_REPOS` "
            "env variable must be provided"
        )

        with raises(SystemExit, match=message):
            fetch_repos(runner, **kwargs)  # pyright: ignore[reportAny]


class TestCheckReposClean:
    @staticmethod
    def test_check_says_clean_on_clean_repos(
        runner: Mock,
        repos: list[Path],
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
    ) -> None:
        runner.side_effect = [clean_output for _ in range(len(repos) * 2)]

        check_repos_clean(runner, repos=repos)

        for repo in repos:
            runner.assert_has_calls(
                [
                    call(
                        *get_unsaved_changes_args(repo),
                        capture_output=True,
                    ),
                    call(
                        *get_unpushed_commits_args(repo),
                        capture_output=True,
                    ),
                ]
            )
        assert_clean_message_shown(capsys.readouterr().out)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unsaved_changes(
        runner: Mock,
        repo1: Path,
        capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes],
    ) -> None:
        runner.side_effect = [unsaved_changes_output]

        check_repos_clean(runner, repos=[repo1])

        runner.assert_called_once_with(
            *get_unsaved_changes_args(repo1),
            capture_output=True,
        )
        assert_repo_not_clean(repo1, capsys.readouterr().err)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unpushed_commits(
        runner: Mock,
        repo1: Path,
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes],
    ) -> None:
        runner.side_effect = [clean_output, unpushed_commits_output]

        check_repos_clean(runner, repos=[repo1])

        runner.assert_has_calls(
            [
                call(
                    *get_unsaved_changes_args(repo1),
                    capture_output=True,
                ),
                call(
                    *get_unpushed_commits_args(repo1),
                    capture_output=True,
                ),
            ]
        )
        assert_repo_not_clean(repo1, capsys.readouterr().err)

    @staticmethod
    def test_check_exits_with_not_a_repo_error_on_invalid_repo(
        runner: Mock,
        repo1: Path,
    ) -> None:
        runner.side_effect = CalledProcessError(128, "command")

        with raises(SystemExit, match=f"Not a git repository: {repo1.expanduser()}"):
            check_repos_clean(runner, repos=[repo1])

        runner.assert_called_once_with(
            *get_unsaved_changes_args(repo1),
            capture_output=True,
        )

    @staticmethod
    def test_check_reraises_unhandled_error(runner: Mock, repo1: Path) -> None:
        exception = CalledProcessError(1, "command")
        runner.side_effect = exception
        message = "Command 'command' returned non-zero exit status 1."

        with raises(CalledProcessError, match=message):
            check_repos_clean(runner, repos=[repo1])

        runner.assert_called_once_with(
            *get_unsaved_changes_args(repo1), capture_output=True
        )

    @staticmethod
    @mark.usefixtures("set_repos_env")
    def test_check_uses_env_as_default(
        runner: Mock,
        repos: list[Path],
        capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes],
    ) -> None:
        runner.return_value = unsaved_changes_output

        check_repos_clean(runner)

        assert_repos_not_clean(repos, capsys.readouterr().err)


class TestApp:
    @staticmethod
    @mark.usefixtures("set_repos_env", "set_dotfiles_env")
    def test_main_dry_run_prints_expected_output_and_exits(
        cli_runner: CliRunner,
        repos: list[Path],
    ) -> None:
        result = cli_runner.invoke(app, "--dry-run", catch_exceptions=False)

        assert str(tuple(get_fetch_dotfiles_args())) in result.stdout
        assert "{check_dotfiles_clean(cmd_runner)}" in result.stdout
        for repo in repos:
            assert str(tuple(get_git_fetch_args(repo))) in result.stdout
        assert "{check_repos_clean(cmd_runner)}" in result.stdout
        assert result.exit_code == 0

    @staticmethod
    @mark.usefixtures("set_dotfiles_env")
    def test_main_dry_run_with_subcommand_prints_its_messages(
        cli_runner: CliRunner,
    ) -> None:
        result = cli_runner.invoke(
            app, ["--dry-run", "fetch-dotfiles"], catch_exceptions=False
        )
        assert str(tuple(get_fetch_dotfiles_args())) in result.stdout
