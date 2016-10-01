"""
The main module of the program. As a main, you are just expected to run it.

As of right now, only supported argument is a command to run the engine process, and it is expected to be encased in quotes.
Note that this command will run as a shell script with all relevant privilages! Be careful not to use "cd /; rm -rf *" as your engine command!
"""
import sys
import os
import subprocess
import logging

from htpclient.htp_controller import HTPController
from htpclient.web_client import HecksWebClient

# This part seems to be pythonian necessary evil...
try:
    os.makedirs("logs", exist_ok=True)
except:
    pass

logging.basicConfig(filename='logs/main.log', level=logging.DEBUG, format='%(asctime)s : %(name)s : %(levelname)s : %(message)s')
logging = logging.getLogger(__name__)
# End of necessary evil

RED = "R"
BLUE = "B"

WAIT_TIMEOUT = 1200  # It's going to take a lot to make us give up...


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
    engine_color = web_client.start_game()
    if engine_color is None:
        logging.error('Received color None from web client. Unable to start game.')
        exit(-1)

    enemey_color = (BLUE if engine_color == RED else RED)

    while True:
        move = web_client.wait_for_move(enemey_color, timeout=WAIT_TIMEOUT)
        if move:
            controller.command_play(enemey_color, move)

        played_succesfully = False
        while not played_succesfully:
            controller.command_genmove(engine_color)
            move = controller.move_queue.get()
            logging.info("Got move {}, attempting to play it.".format(repr(move)))
            played_succesfully = web_client.play_move(move, engine_color)


def cli_main():
    """ Function to be used as CLI entry point. """

    args = sys.argv[1:]
    if len(args) != 3:
        print("Invalid number of arguments.")
        print("Usage: python main.py \"engine command\" username password")
        exit(-1)

    main(*args)


if __name__ == "__main__":
    cli_main()
