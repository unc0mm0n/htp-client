"""
The HTP class uses two pipes to manage communication between the client and the program. It accepts two pipes as arguments, pipe_in and pipe_out.
HTP will send commands to the engine through pipe_out, and read the responses from pipe_in.
"""

from queue import Queue
from threading import Thread


class HTPController(object):
    """
    The controller class for the protocol.

    Use HTPController.send, or one of the command functions, to send commands pipe_out, and read responses from the HTPController.responses Queue.
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

        self.responses = Queue()

        worker_thread = Thread(target=self._reader, name="pipe-in-reader")
        worker_thread.daemon = True
        worker_thread.start()

    def _reader(self):
        """ Intended to run as a thread, continually calls readline() on pipe_in and places the input in self.responses. """
        while True:
            self.responses.put(self._pipe_in.readline())
