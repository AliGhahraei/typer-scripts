#!/usr/bin/env python3
from _pytest.capture import CaptureResult
from pytest import CaptureFixture, raises
from typer import Exit

from typer_scripts.core import CoreException
from typer_scripts.typer_tools import App


class TestApp:
    @staticmethod
    def test_callback_catches_core_exception(capsys: CaptureFixture[str]):
        app_ = App()

        @app_.callback()
        def callback() -> None:
            raise CoreException("message")

        callback()

        assert "message\n" == capsys.readouterr().err

    @staticmethod
    def test_callback_prints_message_for_unhandled_errors(
        capsys: CaptureFixture[str],
    ):
        app_ = App()

        @app_.callback()
        def callback() -> None:
            raise Exception("message")

        with raises(Exception):
            callback()

        assert "Unhandled error, printing traceback:\n" == capsys.readouterr().err

    @staticmethod
    def test_command_catches_core_exception(capsys: CaptureFixture[str]):
        app_ = App()

        @app_.command()
        def command() -> None:
            raise CoreException("message")

        command()

        assert "message\n" == capsys.readouterr().err

    @staticmethod
    def test_command_prints_message_for_unhandled_errors(
        capsys: CaptureFixture[str],
    ):
        app_ = App()

        @app_.command()
        def command() -> None:
            raise Exception("message")

        with raises(Exception):
            command()

        assert "Unhandled error, printing traceback:\n" == capsys.readouterr().err

    @staticmethod
    def test_command_exits_without_message_when_it_raises_exit(
        capsys: CaptureFixture[str],
    ):
        app_ = App()

        @app_.command()
        def command() -> None:
            raise Exit(code=1)

        with raises(Exit):
            command()

        assert capsys.readouterr() == CaptureResult("", "")
