"""
The main module of the program. As a main, you are just expected to run it.

As of right now, only supported argument is a command to run the engine process, and it is expected to be encased in quotes.
Note that this command will run as a shell script with all relevant privilages! Be careful not to use "cd /; rm -rf *" as your engine command!
"""
import sys
import subprocess
import logging

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
    controller = HTPController(prc.stdout, prc.stdin)

    web_client = HecksWebClient(username, password)
    web_client.start_game("TCNwtTzD69AySe3LG")

    while True:
        controller.command_genmove()
        response = controller.responses.get()
        if b"out of data" in response:
            logging.info("got out of data message")
            web_client.disconnect()
            break
        else:
            logging.info("got from engine: {}".format(response))
            web_client.execute_script(response.strip().decode())


if __name__ == "__main__":
    logging.basicConfig(filename='logs/main.log', level=logging.DEBUG, format='%(asctime)s : %(name)s : %(levelname)s : %(message)s')
    logging = logging.getLogger(__name__)

    args = sys.argv[1:]
    if len(args) != 3:
        print("Invalid number of arguments.")
        print("Usage: python main.py \"engine command\" username password")
        exit(-1)
    main(*args)
