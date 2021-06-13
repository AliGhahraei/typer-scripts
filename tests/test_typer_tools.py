#!/usr/bin/env python3
from pytest import fixture, CaptureFixture
from typer import Option
from typer.testing import CliRunner

from typer_scripts.typer_tools import Typer


@fixture
def cli_runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


class TestTyperWithOptionDefault:
    @staticmethod
    @fixture
    def callback_default() -> str:
        return 'callback_default'

    @staticmethod
    @fixture
    def command_default() -> str:
        return 'command_default'

    @staticmethod
    @fixture
    def app(callback_default: str, command_default: str) -> Typer:
        app_ = Typer()

        @app_.callback(invoke_without_command=True)
        def main(message: str = Option(callback_default)) \
                -> None:
            print(message)

        @app_.command()
        def command_name(message: str = Option(command_default)):
            print(message)

        return app_

    @staticmethod
    @fixture
    def command_name() -> str:
        return 'command-name'

    @staticmethod
    def test_callback_gets_default_value_when_invoked_with_typer(
            app: Typer, cli_runner: CliRunner, callback_default: str,
    ) -> None:
        result = cli_runner.invoke(app, catch_exceptions=False)

        assert callback_default in result.stdout

    @staticmethod
    def test_callback_gets_default_value_when_invoked_as_function(
            app: Typer, capsys: CaptureFixture[str], callback_default: str,
    ) -> None:
        f = app.registered_callback.callback  # type: ignore[union-attr]

        f()  # type:ignore[misc]

        assert callback_default in capsys.readouterr().out

    @staticmethod
    def test_callback_gets_keyword_value_when_invoked_with_typer(
            app: Typer, cli_runner: CliRunner,
    ) -> None:
        result = cli_runner.invoke(app, ['--message', 'kwarg'],
                                   catch_exceptions=False)

        assert 'kwarg' in result.stdout

    @staticmethod
    def test_callback_gets_positional_value_when_invoked_as_function(
            app: Typer, capsys: CaptureFixture[str],
    ) -> None:
        f = app.registered_callback.callback  # type: ignore[union-attr]

        f('positional')  # type:ignore[misc]

        assert 'positional' in capsys.readouterr().out

    @staticmethod
    def test_command_gets_default_value_when_invoked_as_function(
            app: Typer, capsys: CaptureFixture[str], command_default: str,
    ) -> None:
        f = app.registered_commands[0].callback

        f()  # type:ignore[misc]

        assert command_default in capsys.readouterr().out


class TestTyperWithPositionalParamAndOptionDefault:
    @staticmethod
    @fixture
    def command_default() -> str:
        return 'command_default'

    @staticmethod
    @fixture
    def app(command_default: str) -> Typer:
        app_ = Typer()

        @app_.command()
        def command_name(nondefault: str,
                         default: str = Option(command_default)):
            print(nondefault)
            print(default)

        return app_

    @staticmethod
    def test_command_gets_all_values_when_invoked_as_function(
            app: Typer, capsys: CaptureFixture[str], command_default: str,
    ) -> None:
        f = app.registered_commands[0].callback

        f('positional')  # type:ignore[misc]

        stdout = capsys.readouterr().out
        assert 'positional' in stdout
        assert command_default in stdout


class TestTyperWithNonTyperDefault:
    @staticmethod
    @fixture
    def command_default() -> str:
        return 'command_default'

    @staticmethod
    @fixture
    def app(command_default: str) -> Typer:
        app_ = Typer()

        @app_.command()
        def command_name(default: str = command_default):
            print(default)

        return app_

    @staticmethod
    def test_command_gets_all_values_when_invoked_as_function(
            app: Typer, capsys: CaptureFixture[str], command_default: str,
    ) -> None:
        f = app.registered_commands[0].callback

        f()  # type:ignore[misc]

        stdout = capsys.readouterr().out
        assert command_default in stdout
