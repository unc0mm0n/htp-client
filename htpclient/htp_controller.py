"""
The HTP class uses two pipes to manage communication between the client and the program. It accepts two pipes as arguments, pipe_in and pipe_out.
HTP will send commands to the engine through pipe_out, and read the responses from pipe_in.
"""

from queue import Queue
from threading import Thread
import logging
import time

logging = logging.getLogger(__name__)

RED = "R"
BLUE = "B"

FAIL_PREFIX = "?"
SUCCESS_PREFIX = "="

PASS = "pass"
RESIGN = "resign"


class HTPController(object):
    """
    The controller class for the protocol.

    Use HTPController.send, or one of the command functions, to send commands to pipe_out, and read moves from HTPController.move_queue
    or errors from HTPController.fail_queue.
    """

    def __init__(self, pipe_in, pipe_out):
        """
        Initialize an engine reading input from pipe_in and sending output to pipe_out.

        This will start a daemon thread reading on std_in and placing responses in Engine.responses. No parsing is done to the responses.

        :param pipe_in: filelike object to read data from. Usually a pipe. Will be read in a loop.
        :param pipe_out: filelike object to write data to. Usually a pipe.
        """
        self._pipe_in = pipe_in
        self._pipe_out = pipe_out

        self._response_queue = Queue()

        self.move_queue = Queue()
        self.fail_queue = Queue()

        reader_thread = Thread(target=self._reader, name="pipe-in-reader")
        reader_thread.daemon = True
        reader_thread.start()

        parser_thread = Thread(target=self._response_parser, name="response-queue-parser")
        parser_thread.daemon = True
        parser_thread.start()

    def command_genmove(self, color):
        """
        [Command] Tell the engine to decide on a move for given color, which he will return as a coordinates response
        and will be stored in self.move_queue.
        """
        if color.upper() not in (RED, BLUE):
            raise ValueError("Invalid color to command genmove.")
        self.send_command("genmove {}\n".format(color.upper()))

    def command_play(self, color, coordinates):
        """ [Command] Tell the engine to make given move internally. """
        if color.upper() not in (RED, BLUE):
            raise ValueError("Invalid color to command play: {}".format(color))
        if not self.valid_htp_coordinates(coordinates):
            raise ValueError("Invalid coordinates to command play: {}".format(coordinates))

        self.send_command("play {} {}\n".format(color, coordinates))

    def send_command(self, cmd):
        """ Send any command given as cmd to _pipe_out, with no validations. Accepts either str or bytes object. """
        if isinstance(cmd, str):
            cmd = cmd.encode()  # Make sure our command is in bytes

        logging.info("Sending command: {}".format(repr(cmd)))
        self._pipe_out.write(cmd)
        self._pipe_out.flush()

    def _reader(self):
        """ Intended to run as a thread, continually calls readline() on pipe_in and places the input in self.responses. """
        while True:
            in_data = self._pipe_in.readline()
            if in_data:
                logging.info("[READER] Adding response to Queue: {}".format(repr(in_data)))
                self._response_queue.put(in_data)
            time.sleep(0.2)

    def _response_parser(self):
        """ Intented to run as a thread, continually reads from self._response_queue and parses the results. """
        while True:
            response = self._response_queue.get().decode()  # We want to work with unicode strings, not bytes.
            logging.info("[PARSER] Parsing response: {}".format(repr(response)))
            response = response.strip().replace("\t", " ")

            response_list = response.split(" ", maxsplit=1)  # An expected response is formatted as =[id] response_data
            if len(response_list) == 1:
                logging.debug("Empty response, skipping.")
                continue
            else:  # The length of the split can't be more than 2..
                result, response_data = response_list
                logging.debug("Result split to {}, {}".format(repr(result), repr(response_data)))

            if result[0] == FAIL_PREFIX:
                logging.info("[PARSER] Adding to failed queue: {}".format(repr(response)))
                self.fail_queue.put(response)
            elif result[0] == SUCCESS_PREFIX:
                logging.debug("[PARSER] Checking if {} is a valid coordinate".format(repr(response_data)))
                if self.valid_htp_coordinates(response_data):
                    logging.info("[PARSER] Adding to move queue: {}".format(repr(response_data)))
                    self.move_queue.put(response_data)

            # For the initial naive implementation we will just assume that any success response whose data is valid coordinates is a move.

    @staticmethod
    def valid_htp_coordinates(coordinates):
        """ Return True if given coordinates are valid HTP coordinates. """
        if coordinates == "pass" or coordinates == "resign":
            return True

        if not (2 <= len(coordinates) <= 3):
            return False

        row, col = coordinates[0], coordinates[1:]
        try:

            row_val = ord(row.lower()) - ord('a') + 1
            col = int(col)

            if row_val <= 5:
                max_col = 9 + 2 * row_val
            else:
                max_col = 9 + 2 * (11 - row_val)
            return row.isalpha() and 'a' <= row.lower() <= 'j' and 1 <= int(col) <= max_col
        except ValueError:
            return False


if __name__ == "__main__":
    import random
    import itertools

    # Test valid_htp_coordinates
    moves = []
    for row in range(5):
        for col in range(1, 11 + 2 * row):
            row_letter = chr(ord('a') + row)
            htp_vertex = "{}{}".format(row_letter, col)
            moves.append(htp_vertex)

            reflected_row_letter = chr(ord('a') + (9 - row))
            htp_reflected_vertex = "{}{}".format(reflected_row_letter, col)
            moves.append(htp_reflected_vertex)
    random.shuffle(moves)
    logging.debug("Moves: {}".format(moves))

    for value, expected in map(lambda x: (x, True), moves):
        got = HTPController.valid_htp_coordinates(value)
        print(value, repr(got), repr(expected))
        assert got == expected

    for value, expected in (("pass", True), ("resign", True), ("A5", True), ("B13", True),
                            ("11", False), ("a12", False), ("", False), ("aa", False), ("1a", False)):
        got = HTPController.valid_htp_coordinates(value)
        print(value, repr(got), repr(expected))
        assert got == expected
