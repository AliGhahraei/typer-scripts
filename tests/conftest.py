from pytest import fixture

from typer.testing import CliRunner


@fixture
def cli_runner() -> CliRunner:
    return CliRunner(mix_stderr=False)
