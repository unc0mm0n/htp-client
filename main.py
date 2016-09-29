"""
The main module of the program. As a main, you are just expected to run it.

As of right now, only supported argument is a command to run the engine process, and it is expected to be encased in quotes.
Note that this command will run as a shell script with all relevant privilages! Be careful not to use "cd /; rm -rf *" as your engine command!
"""
import sys
import subprocess

from htp_controller import HTPController
from web_client import HecksWebClient


def main(command, username, password):
    """
    The main method of the program.

    Will run the client, open a subprocess with pipe to the given command, and pass them to htp_wrapper.

    Will manage the required interaction between them.

    :param run_cmd: the command to run as a subprocess
    """
    prc = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    controller = HTPController(prc.stdin, prc.stdout)

    web_client = HecksWebClient(username, password)


if __name__ == "__main__":
    if len(sys.argv != 3):
        print("Invalid number of arguments.")
        print("Usage: python main.py \"engine command\" username password")
        exit(-1)
    main(*sys.argv)
