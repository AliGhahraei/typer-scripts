#!/usr/bin/env python3
from pathlib import Path
from collections.abc import Iterable
from subprocess import CalledProcessError, CompletedProcess
from typing import Any
from unittest.mock import Mock, call, patch

from pytest import CaptureFixture, fixture, raises, mark, MonkeyPatch
from typer.testing import CliRunner

from typer_scripts.core import RunMode
from typer_scripts.repos import (
    check_repos_clean,
    check_dotfiles_clean,
    fetch_repos,
    fetch_dotfiles,
    app,
)

DARWIN = "Darwin"
LINUX = "Linux"
UNKNOWN_OS = "Unknown OS"


@fixture
def run():
    with patch("typer_scripts.repos.run") as run_mock:
        yield run_mock


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


def assert_repos_fetched(repos: Iterable[Path], run: Mock) -> None:
    run.assert_has_calls(
        [call(get_git_fetch_args(repo), RunMode.DEFAULT) for repo in repos]
    )


def get_dotfiles_prefix() -> list[str]:
    return ["git", "--git-dir=TEST_DOTFILES_REPO"]


def get_fetch_dotfiles_args() -> list[str]:
    return [*get_dotfiles_prefix(), "fetch"]


def get_git_fetch_args(repo: Path) -> list[str | Path]:
    return ["git", "-C", repo.expanduser(), "fetch"]


def get_command_prefix_for_unpushed_commits() -> list[str]:
    return ["log", "--branches", "--not", "--remotes", "--oneline"]


def get_unpushed_commits_args(repo: Path) -> list[str | Path]:
    return ["git", "-C", repo.expanduser(), *get_command_prefix_for_unpushed_commits()]


def get_command_prefix_for_unsaved_changes() -> list[str]:
    return ["status", "--ignore-submodules", "--porcelain"]


def get_unsaved_changes_args(repo: Path) -> list[str | Path]:
    return ["git", "-C", repo.expanduser(), *get_command_prefix_for_unsaved_changes()]


class TestFetchDotfiles:
    @staticmethod
    def test_fetch_shows_fetching_dotfiles_message(capsys: CaptureFixture[str]) -> None:
        fetch_dotfiles(Mock())

        assert_stdout("Fetching dotfiles", capsys.readouterr().out)

    @staticmethod
    @mark.usefixtures("set_dotfiles_env")
    def test_fetch_runs_fetch() -> None:
        cmd_runner = Mock()
        fetch_dotfiles(cmd_runner)

        cmd_runner.assert_called_once_with(get_fetch_dotfiles_args())


@mark.usefixtures("set_dotfiles_env")
class TestCheckDotfilesClean:
    @staticmethod
    @mark.usefixtures("run")
    def test_check_shows_checking_dotfiles_message(capsys: CaptureFixture[str]) -> None:
        check_dotfiles_clean()

        assert_stdout("Checking dotfiles", capsys.readouterr().out)

    @staticmethod
    def test_check_shows_not_clean_on_dotfiles_with_unsaved_changes(
        run: Mock,
        capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [unsaved_changes_output]

        check_dotfiles_clean()

        run.assert_called_once_with(
            [*get_dotfiles_prefix(), *get_command_prefix_for_unsaved_changes()],
            RunMode.DEFAULT,
            capture_output=True,
        )
        assert_stdout("Dotfiles were not clean", capsys.readouterr().out)

    @staticmethod
    def test_check_shows_not_clean_on_dotfiles_with_unpushed_commits(
        run: Mock,
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [clean_output, unpushed_commits_output]

        check_dotfiles_clean()

        run.assert_has_calls(
            [
                call(
                    [*get_dotfiles_prefix(), *get_command_prefix_for_unsaved_changes()],
                    RunMode.DEFAULT,
                    capture_output=True,
                ),
                call(
                    [
                        *get_dotfiles_prefix(),
                        *get_command_prefix_for_unpushed_commits(),
                    ],
                    RunMode.DEFAULT,
                    capture_output=True,
                ),
            ]
        )
        assert_stdout("Dotfiles were not clean", capsys.readouterr().out)

    @staticmethod
    def test_check_shows_clean_on_clean_dotfiles(
        run: Mock,
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [clean_output] * 2

        check_dotfiles_clean()

        run.assert_has_calls(
            [
                call(
                    [*get_dotfiles_prefix(), *get_command_prefix_for_unsaved_changes()],
                    RunMode.DEFAULT,
                    capture_output=True,
                ),
                call(
                    [
                        *get_dotfiles_prefix(),
                        *get_command_prefix_for_unpushed_commits(),
                    ],
                    RunMode.DEFAULT,
                    capture_output=True,
                ),
            ]
        )
        assert_stdout("Dotfiles were clean!", capsys.readouterr().out)


class TestFetchRepos:
    @staticmethod
    @mark.usefixtures("run")
    def test_fetch_shows_fetching_repos_message(
        repos: list[Path],
        capsys: CaptureFixture[str],
    ) -> None:
        fetch_repos(repos=repos)

        assert_stdout("Fetching repos", capsys.readouterr().out)

    @staticmethod
    def test_fetch_is_run_for_every_repo(run: Mock, repos: list[Path]) -> None:
        fetch_repos(repos=repos)

        assert_repos_fetched(repos, run)

    @staticmethod
    @mark.usefixtures("set_repos_env")
    def test_fetch_uses_env_as_default(run: Mock, repos: list[Path]) -> None:
        fetch_repos()

        assert_repos_fetched(repos, run)

    @staticmethod
    @mark.parametrize("kwargs", [{}, {"repos": None}, {"repos": list[Path]()}])
    def test_fetch_exits_without_repos(
        kwargs: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    ) -> None:
        message = (
            "Either the `repos` argument or the `TYPER_SCRIPTS_REPOS` "
            "env variable must be provided"
        )

        with raises(SystemExit, match=message):
            fetch_repos(**kwargs)  # pyright: ignore[reportAny]


class TestCheckReposClean:
    @staticmethod
    def test_check_says_clean_on_clean_repos(
        run: Mock,
        repos: list[Path],
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [clean_output for _ in range(len(repos) * 2)]

        check_repos_clean(repos=repos)

        for repo in repos:
            run.assert_has_calls(
                [
                    call(
                        get_unsaved_changes_args(repo),
                        RunMode.DEFAULT,
                        capture_output=True,
                    ),
                    call(
                        get_unpushed_commits_args(repo),
                        RunMode.DEFAULT,
                        capture_output=True,
                    ),
                ]
            )
        assert_clean_message_shown(capsys.readouterr().out)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unsaved_changes(
        run: Mock,
        repo1: Path,
        capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [unsaved_changes_output]

        check_repos_clean(repos=[repo1])

        run.assert_called_once_with(
            get_unsaved_changes_args(repo1),
            RunMode.DEFAULT,
            capture_output=True,
        )
        assert_repo_not_clean(repo1, capsys.readouterr().out)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unpushed_commits(
        run: Mock,
        repo1: Path,
        capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes],
    ) -> None:
        run.side_effect = [clean_output, unpushed_commits_output]

        check_repos_clean(repos=[repo1])

        run.assert_has_calls(
            [
                call(
                    get_unsaved_changes_args(repo1),
                    RunMode.DEFAULT,
                    capture_output=True,
                ),
                call(
                    get_unpushed_commits_args(repo1),
                    RunMode.DEFAULT,
                    capture_output=True,
                ),
            ]
        )
        assert_repo_not_clean(repo1, capsys.readouterr().out)

    @staticmethod
    def test_check_exits_with_not_a_repo_error_on_invalid_repo(
        run: Mock,
        repo1: Path,
    ) -> None:
        run.side_effect = CalledProcessError(128, "command")

        with raises(SystemExit, match=f"Not a git repository: {repo1.expanduser()}"):
            check_repos_clean(repos=[repo1])

        run.assert_called_once_with(
            get_unsaved_changes_args(repo1),
            RunMode.DEFAULT,
            capture_output=True,
        )

    @staticmethod
    def test_check_reraises_unhandled_error(run: Mock, repo1: Path) -> None:
        exception = CalledProcessError(1, "command")
        run.side_effect = exception
        message = "Command 'command' returned non-zero exit status 1."

        with raises(CalledProcessError, match=message):
            check_repos_clean(repos=[repo1])

        run.assert_called_once_with(
            get_unsaved_changes_args(repo1), RunMode.DEFAULT, capture_output=True
        )

    @staticmethod
    @mark.usefixtures("set_repos_env")
    def test_check_uses_env_as_default(
        run: Mock,
        repos: list[Path],
        capsys: CaptureFixture[str],
        unsaved_changes_output: CompletedProcess[bytes],
    ) -> None:
        run.return_value = unsaved_changes_output

        check_repos_clean()

        assert_repos_not_clean(repos, capsys.readouterr().out)


class TestApp:
    @staticmethod
    @mark.usefixtures("set_repos_env", "set_dotfiles_env")
    def test_main_dry_run_prints_expected_output_and_exits(
        cli_runner: CliRunner,
        repos: list[Path],
    ) -> None:
        result = cli_runner.invoke(app, "--dry-run", catch_exceptions=False)

        assert str(tuple(get_fetch_dotfiles_args())) in result.stdout
        assert "function:check_dotfiles_clean" in result.stdout
        for repo in repos:
            assert str(tuple(get_git_fetch_args(repo))) in result.stdout
        assert "function:check_repos_clean" in result.stdout
        assert result.exit_code == 0

    @staticmethod
    def test_main_dry_run_with_subcommand_exits_with_error(
        cli_runner: CliRunner,
    ) -> None:
        result = cli_runner.invoke(
            app, ["--dry-run", "fetch-dotfiles"], catch_exceptions=False
        )
        assert "Cannot pass dry-run and a subcommand" in result.stderr
        assert result.exit_code == 1
