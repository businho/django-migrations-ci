from django_migrations_ci import shell


def test_shell_ok():
    stdout, stderr = shell.exec("ls")
    assert b"\nREADME.md\n" in stdout
    assert stderr == b""


def test_shell_error():
    stdout, stderr = shell.exec("oof")
    assert stdout == b""
    assert stderr == b"/bin/sh: 1: oof: not found\n"


def test_shell_custom_env():
    stdout, stderr = shell.exec("echo $FOO", env={"FOO": "BAR"})
    assert stdout == b"BAR\n"
    assert stderr == b""
