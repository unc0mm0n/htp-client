"""
The web client uses Selenium with Chrome (future: or Firefox) to communicate with the hecks.space website and relay events to the HTP controller,
which will send pipe them to the engine.
"""
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from queue import PriorityQueue
import threading
import logging
import time
import sys, os

# This is just to prevent selenium from logging too much (Yeah I know, it's ugly over here..)
selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
# Only display possible problems
selenium_logger.setLevel(logging.WARNING)
logging = logging.getLogger(__name__)

# Server constants
HECKS_URL = "https://hecks.space"
USERNAME_FIELD_ID = "at-field-username"
PASSWORD_FIELD_ID = "at-field-password"
SUBMIT_BUTTON_ID = "at-btn"
MATCH_BUTTON_CLASS = "automatchInsert"

SERVER_PASS = "pass"
SERVER_RESIGN = "resign"

# JS Commands - Most commands have empty spaces which should be filled with COMMAND.format(parameters=values)
BOARD_INFO_JS = "return this.game"  # We poll this command to monitor the state of the game.
MAKE_MOVE_JS = 'Meteor.call("games.makeTurn", {y}, {x}, "{game_id}")'  # This is the command used by the server  to play a move.
PASS_JS = 'Meteor.call("games.pass", "{game_id}")'  # This is the command used by the server to pass.
RESIGN_JS = 'Meteor.call("games.resign", "{game_id}")'

# HTP constants
HTP_PASS = "pass"
HTP_RESIGN = "resign"
RED = "R"
BLUE = "B"

# Default settings
DEFAULT_POLL_DELAY = 0.1
DEFAULT_PAGE_WAIT_TIMEOUT = 20

# Time in seconds it will take before notifying a move failed. This shoudln't be too long in case of actual bad moves.
# But should be long enoug for the client to process the move request.
MOVE_WAIT_TIME = 5

POLL_PRIORITY = 10  # Lower number is higher priority
MOVE_PRIORITY = 3
QUIT_PRIORITY = 1


class HecksWebClient(object):
    """
    The class that manages the web client.

    Supports connection and starting a game, and continuesly polls "this.game" JS object for data about the current game state and
    the turns.
    """

    def __init__(self, username, password):
        """
        Initialize a new client. Call connect to make is start

        :param username: username to connect as
        :param password: password to use for connection
        """

        self.game = None  # Here we will hold the game object updated by self._poll_game
        self.username = username
        self.__password = password

        # Oww.. My Eyes... :'(
        if sys.platform in ('win32', 'cygwin'):
            chrome_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                       'selenium_drivers/chromedriver.exe')
            driver_log_path = 'nul'
        elif sys.platform == "linux2":
            chrome_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                       'selenium_drivers/chromedriver')
            driver_log_path = '/dev/null'
        else:
            raise ClientError("Operation system is not currently supported. ")

        if chrome_path:
            logging.info("Starting web driver at {}, logs will (not) be saved at {}".format(chrome_path, driver_log_path))
            self._driver = webdriver.Chrome(chrome_path, service_log_path=driver_log_path)

        self._execution_priority_queue = PriorityQueue()

        self._stop_poll_event = threading.Event()

        executor_thread = threading.Thread(target=self._executor, name="client-executor")
        executor_thread.daemon = True
        executor_thread.start()

    @property
    def color(self):
        """ Returns our color in the game, or None if we are not in a game (or not playing) """
        if not self.game:
            return None

        if self.game["name1"] == self.username:
            return BLUE
        elif self.game["name2"] == self.username:
            return RED
        else:
            return None

    @property
    def current_player(self):
        if not self.game:
            return None
        try:
            return BLUE if self.game["turn"] % 2 == 0 else RED
        except Exception:
            logging.error("No turn variable in game.. {}".format(self.game))
            return None

    @property
    def in_game(self):
        return self.game is None or not self.game.get("result", False)

    def connect(self):
        """
        Launch a web page to hecks and attempt to connect to given username and password.

        :param username: username to connect as
        :param password: password to use for connection
        """

        logging.info("Connecting to Hecks at {}".format(HECKS_URL))
        self._driver.get(HECKS_URL)

        if "login" not in self._driver.current_url:
            raise ClientError("Unable to reach login page. Are you already logged in?")

        # Find the fields and submit
        self._driver.find_element_by_id(USERNAME_FIELD_ID).send_keys(self.username)
        self._driver.find_element_by_id(PASSWORD_FIELD_ID).send_keys(self.__password)
        self._driver.find_element_by_id(SUBMIT_BUTTON_ID).click()

        WebDriverWait(self._driver, DEFAULT_PAGE_WAIT_TIMEOUT).until(lambda x: "chat" in x.current_url)

    def disconnect(self):
        """ Close the webdriver window and stop the polling session. """
        self._stop_poll_event.set()
        self._execution_priority_queue.put((QUIT_PRIORITY, "return", self._driver.close))

    def play_move(self, move, color):
        """
        Accept a move as an HTP coordinates str, and attempt to play it on the board.

        Return True on success or Fail on failure.

        The color option is redundant for now, as we only play games where we have one color, but it might be useful in the future
        if we want to implement move analysis.
        :param move: HTP notation of move to play.
        :param color: HTP notation of color to play ("R" or "B")
        :return: True if move was played, False otherwise.
        """
        logging.info("Playing move: {} for player: {}".format(repr(move), format(repr(color))))
        if not self.in_game:
            raise ClientError("play_move called with no game active")

        if self.current_player != color:
            return False

        if move == HTP_PASS:
            js_command = PASS_JS.format(game_id=self.game["_id"])
        elif move == HTP_RESIGN:
            js_command = RESIGN_JS.format(game_id=self.game["_id"])
        else:
            last_move_str = self.game["lastMove"]
            last_move = self.parse_server_coordinates(last_move_str)

            if last_move == move:
                return False

            y, x = self.parse_htp_coordinates(move)

            if len(self.game["dotsData"][y]) <= x or self.game["dotsData"][y][x] != 0:
                logging.warning("Move {} wasn't played! It was deemed an invalid coordinate (not on the board or not empty)".format(repr(move)))
                return False

            js_command = MAKE_MOVE_JS.format(x=x, y=y, game_id=self.game["_id"])

        logging.debug("Sending command for execution: {}".format(repr(js_command)))

        self._execution_priority_queue.put((MOVE_PRIORITY, js_command, None))

        w = 0

        while True:  # Because quasi-infinite loops are fun.

            if self.current_player != color:
                return True
            logging.debug("Move {} still wasn't updated. wait time: {} timeout: {}".format(repr(move), repr(w), repr(MOVE_WAIT_TIME)))
            time.sleep(DEFAULT_POLL_DELAY)  # We sleep the approximate time it takes the game to update, for obvious reasons.

            w += DEFAULT_POLL_DELAY

            if w > MOVE_WAIT_TIME:
                logging.warning("Move {} wasn't played! It might be invalid or the server isn't responding.".format(repr(move)))
                return False

    def start_game(self, id=None):
        """
        Try to start a new game on the web server, and block until it succeeds.

        If a game id is passed, the client will attempt to connect to given ID instead of starting a new game.
        Will return the client's color in the game.
        :param id: ID of game to join. Can be used to reconnect or to observe a game.
        :return: The client's color in the game
        """
        if id is None:
            logging.info("Starting a new game.")
            self._driver.get(HECKS_URL + "/play")

            if "play" not in self._driver.current_url:
                raise ClientError("Unable to reach play page. Are you logged in?")

            WebDriverWait(self._driver, DEFAULT_PAGE_WAIT_TIMEOUT).until(lambda x: x.find_element_by_class_name(MATCH_BUTTON_CLASS))

            self._driver.find_element_by_class_name(MATCH_BUTTON_CLASS).click()
        else:
            logging.info("Connecting to existing game: {}".format(repr(id)))
            self._driver.get(HECKS_URL + "/game/{}".format(id))

        self._stop_poll_event.clear()
        poll_game_thread = threading.Thread(target=self._poll_game, name="game-poll")
        poll_game_thread.daemon = True
        poll_game_thread.start()

        while self.game is None:
            time.sleep(0.5)

        logging.info("Game started! We are playing as: {}".format(repr(self.color)))
        return self.color

    def wait_for_move(self, player, timeout=None):
        """
        Block until a move is played by the player or until maximum timeout is reached. Return immediately if it's not the player's turn.

        Raise TimeoutError if timeout is reached without play.
        :param player: color of player to play.
        :param timeout: (default=None) maximum time to wait for move. If None will block indefinitely.
        :return: HTP-Compliant notation of the last move played.
        """
        if not self.in_game:
            raise ClientError("wait_for_move called with no game active")

        logging.info("Waiting for move for player: {}".format(repr(player)))

        w = 0
        while player == self.current_player:
            time.sleep(0.2)
            w += 0.2
            if timeout and w > timeout:
                raise TimeoutError("wait for move timeout expired")

        return self.parse_server_coordinates(self.game["lastMove"])

    def _executor(self):
        """
        Executes scripts one by one from the execution priority queue.

        This method must run in it's own thread.

        The queue is expected to contain tuples for priority, script, callback function. The callback function will be called with the return value of
        the execution. The second element of the tuple can be None, in which case nothing will be done with the return value.
        """
        while True:
            priority, script, function = self._execution_priority_queue.get()
            if priority < POLL_PRIORITY:
                logging.debug("[EXECUTOR] Executing script: {}".format(repr(script)))
            out = self._driver.execute_script(script)
            if function is not None:
                function(out)

    def _poll_game(self, poll_delay=DEFAULT_POLL_DELAY):
        """ This thread should be running at all times as long as a game is going, as it updates the game information in the client. """
        def update_game(game):
            self.game = game

        self.poll_delay = poll_delay
        while not self._stop_poll_event.is_set():
            self._execution_priority_queue.put((POLL_PRIORITY, BOARD_INFO_JS, update_game))
            time.sleep(poll_delay)

    @staticmethod
    def parse_htp_coordinates(coordinates_string):
        """
        Accept HTP-Notation vertex and parse them into an (x,y) tuple which we can format into the hecks.space command,
        or SERVER_PASS, SERVER_RESIGN if applicable.

        :param coordinates_string: HTP-compliant coordinates string
        :return: (y,x) tuple for integer value for the coordinates, or SERVER_PASS, SERVER_RESIGN. None on invalid input
        """
        if not coordinates_string:
            return None

        if coordinates_string == SERVER_PASS:
            return HTP_PASS
        elif coordinates_string == SERVER_RESIGN:
            return HTP_RESIGN

        try:
            y, x = coordinates_string[0], int(coordinates_string[1:])

            if not y.isalpha():
                logging.warning("Invalid input to parse_htp_coordinates: {}".format(repr(coordinates_string)))
                return None
            y = (ord(y.lower()) - ord('a')) + 1  # convert 'a'-'j' into 1-10

            if y <= 5:
                server_x = int(x) + (4 - y)  # The first coordinate of a row of distance d from the center is moved d + 1
                                             # spots to the right, so we add them back.
            else:
                server_x = int(x) + (y - 7)  # Same goes for the top half
        except ValueError:
            logging.warning("Invalid input to parse_htp_coordinates: {}".format(repr(coordinates_string)))
            return None

        if y <= 5:
            # On the bottom half, the even columns of each row are at the bottom
            server_y = 2 * (10 - y) + 1 - x % 2
        else:
            # On the bottom half, it is exactly the opposite.
            server_y = 2 * (10 - y) + x % 2

        if server_x < 0 or server_x > 19 or server_y < 0 or server_y > 20:
            logging.warning("Invalid input to parse_htp_coordinates: {}. Got {}".format(repr(coordinates_string), (y, x)))
            return None

        return server_y, server_x

    @staticmethod
    def parse_server_coordinates(coordinates_string):
        """
        Accept Server-Notation formatted coordinates and parse them into HTP-compliant move

        Will return None if a falsy or invalid input is given.

        :param coordinates_string: Coordinates string in server notation
        :return: HTP-compliant Move or None on invalid string
        """

        if coordinates_string == SERVER_PASS:
            return HTP_PASS
        elif coordinates_string == SERVER_RESIGN:
            return HTP_RESIGN

        if not coordinates_string or len(coordinates_string) != 2:
            return None

        try:
            x, y = (HecksWebClient.one_char_conversion(c) for c in coordinates_string)
        except ValueError:
            logging.warning("Invalid input to parse_server_coordinates: {}".format(repr(coordinates_string)))
            return None
        htp_y = 10 - y // 2  # convert '0-19' into '10-1'

        # On odd rows, the sum of coordinates is even and on even rows the sum is odd.
        if (x + y + htp_y) % 2 == 0:
            logging.warning("Invalid input to parse_server_coordinates: {}".format(repr(coordinates_string)))
            return None

        if htp_y <= 5:
            max_x = 9 + 2 * y
            htp_x = x - (4 - htp_y)
        else:
            max_x = 9 + 2 * (11 - y)
            htp_x = x - (htp_y - 7)

        if htp_x < 1 or htp_x > max_x or htp_y < 1 or htp_y > 10:
            logging.warning("Invalid input to parse_server_coordinates: {}. got {}".format(repr(coordinates_string), (htp_y, htp_x)))
            return None
        return chr(htp_y + ord('a') - 1) + str(htp_x)

    @staticmethod
    def one_char_conversion(c):
            """ Convert one character to it's base 10 integer value (in server notation, starting from 0). """
            if c.isalpha():
                idx = ord(c.lower()) - ord('a') + 10
            else:
                idx = int(c)

            if idx < 0 or idx > 19:
                msg = "Invalid character for one_char_conversion: {}".format(repr(c))
                raise ValueError(msg)

            return idx


class ClientError(Exception):
    pass


if __name__ == "__main__":

    # Test one_char_conversion
    values = list(range(10)) + [chr(x) for x in range(97, 107)]
    for idx, value in enumerate(values):
        got = HecksWebClient.one_char_conversion(str(value))
        print(value, got, idx)
        assert got == idx

    try:
        HecksWebClient.one_char_conversion('t')
    except ValueError:
        print('t got value error as required')

    try:
        HecksWebClient.one_char_conversion('23')
    except ValueError:
        print('23 got value error as required')

    try:
        HecksWebClient.one_char_conversion('909f')
    except ValueError:
        print('909f got value error as required')

    # Test parse_server_coordinates

    for value, expected in (("00", None), ("40", None), ("41", "j1"), ("50", "j2"), ("51", None), ("60", None), ("61", "j3"),
                            ("45", "h3"), ("0i", None), ("4i", "a1"), ("5j", "a2"), ("5i", None), ("6j", None), ("6i", "a3")):
        got = HecksWebClient.parse_server_coordinates(value)
        print(value, got, expected)
        assert got == expected

    got = HecksWebClient.parse_server_coordinates(SERVER_PASS)
    print(got, HTP_PASS)
    assert got == HTP_PASS

    got = HecksWebClient.parse_server_coordinates(SERVER_RESIGN)
    print(got, HTP_RESIGN)
    assert got == HTP_RESIGN

    got = HecksWebClient.parse_server_coordinates("asdfv3fg3")
    print(got, None)
    assert got is None

    # Test parse_htp_coordinates
    for value, expected in [("a1", (18, 4)), ("f10", (8, 9)), ("j1", (1, 4)), ("j2", (0, 5)), ("j3", (1, 6)),
                            ("j4", (0, 7)), ("j5", (1, 8)), ("j6", (0, 9)), ("j11", (1, 14)), ("j12", (0, 15)),
                            ("I12", (2, 14))]:
        got = HecksWebClient.parse_htp_coordinates(value)
        print(value, got, expected)
        assert got == expected

    for value, expected in [(HTP_PASS, SERVER_PASS), (HTP_RESIGN, SERVER_RESIGN), ("AA", None),
                            ("11", None), ("A1A", None), ("Z1", None), ("z130", None)]:
        got = HecksWebClient.parse_htp_coordinates(value)
        print(value, repr(got), repr(expected))
        assert got == expected

    client = HecksWebClient("asfffd", "asffffd")
