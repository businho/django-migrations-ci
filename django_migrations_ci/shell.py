import logging
import os
from subprocess import PIPE, Popen

logger = logging.getLogger(__name__)


class MigrateCIShellException(Exception):
    pass


def exec(command, env=None):
    logger.info(f"Running shell command {command}")

    subprocess_env = os.environ.copy()
    if env:
        subprocess_env.update(env)

    p = Popen(
        command,
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        env=subprocess_env,
    )
    stdout, stderr = p.communicate()
    if stderr:
        raise MigrateCIShellException(stderr.decode())
    return stdout
