from subprocess import PIPE, Popen


def exec(command, env):
    if "test_test" in command:
        raise Exception(command)

    print("EXEC", command)
    p = Popen(
        command,
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        env=env,
    )
    stdout, stderr = p.communicate()

    if stderr:
        print("EXEC ERROR", command, stdout, stderr)
    return stdout, stderr
