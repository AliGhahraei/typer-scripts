import os
from unittest import mock
from pytest import fixture

from typer.testing import CliRunner


@fixture(scope="session", autouse=True)
def clean_initial_envvars():
    with mock.patch.dict(os.environ, clear=True):
        yield


@fixture
def cli_runner() -> CliRunner:
    return CliRunner(mix_stderr=False)
