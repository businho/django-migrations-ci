import pytest

from django_migrations_ci import shell


def test_shell_ok():
    stdout = shell.exec("ls")
    assert b"\nREADME.md\n" in stdout


def test_shell_error():
    with pytest.raises(shell.MigrateCIShellException, match=r"oof.+not found"):
        shell.exec("oof")


def test_shell_custom_env():
    stdout = shell.exec("echo $FOO", env={"FOO": "BAR"})
    assert stdout == b"BAR\n"
