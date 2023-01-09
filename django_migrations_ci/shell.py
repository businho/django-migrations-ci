import logging
from subprocess import PIPE, Popen

logger = logging.getLogger(__name__)


def exec(command, env=None):
    logger.info(f"Running shell command {command}")
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
        logger.error(f"Error running shell command {command}\n{stdout=}\n{stderr=}")
    return stdout, stderr
