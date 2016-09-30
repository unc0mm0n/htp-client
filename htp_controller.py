"""
The HTP class uses two pipes to manage communication between the client and the program. It accepts two pipes as arguments, pipe_in and pipe_out.
HTP will send commands to the engine through pipe_out, and read the responses from pipe_in.
"""

from queue import Queue
from threading import Thread
import logging
import time

logging = logging.getLogger(__name__)


class HTPController(object):
    """
    The controller class for the protocol.

    Use HTPController.send, or one of the command functions, to send commands to pipe_out, and 
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
        self._move_queue = Queue()
        self._fail_queue = Queue()

        worker_thread = Thread(target=self._reader, name="pipe-in-reader")
        worker_thread.daemon = True
        worker_thread.start()

    def command_genmove(self):
        """ [Command] Tell the engine to make a move, which he will return as a response and will be stored in self._move_queue. """
        logging.debug("sending command genmove")
        self._pipe_out.write(b"genmove\n")

        # This actually sends the command..
        self._pipe_out.flush()

    def _reader(self):
        """ Intended to run as a thread, continually calls readline() on pipe_in and places the input in self.responses. """
        while True:
            in_data = self._pipe_in.readline()
            if in_data:
                self._response_queue.put(in_data)
                logging.debug("Adding response to Queue: {}".format(in_data))
            time.sleep(0.2)

    def _response_parser(self):
        """ Intented to run as a thread, continually reads from self._response_queue and parses the results. """
        while True:
            response = self._response_queue.get()
            response.replace("\r", "").replace("\t", " ")

            result, response_data = response.split(" ", maxsplit=1)  # An expected response is formatted as =[id] response_data
            id = None

            if len(result) > 1:
                result, id = result[0], result[1:]

            # For the initial naive implementation we will just assume that any success response with data is a move
