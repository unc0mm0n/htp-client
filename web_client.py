"""
The web client uses Selenium with Firefox (future: or Chrome) to communicate with the hecks.space website and relay events to the HTP controller,
which will send pipe them to the engine.
"""
from selenium import webdriver
import logging
import json

# This is just to prevent selenium from logging too much (Yeah I know, it's ugly over here..)
selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
# Only display possible problems
selenium_logger.setLevel(logging.WARNING)
logging = logging.getLogger(__name__)

HECKS_URL = "https://hecks.space"
USERNAME_FIELD_ID = "at-field-username"
PASSWORD_FIELD_ID = "at-field-password"
SUBMIT_BUTTON_ID = "at-btn"


class HecksWebClient():
    """
    The class that manages the web client.

    Supports connection and starting a game, and continuesly polls "this.game" JS object for data about the current game state and
    the turns.
    """

    def __init__(self, username, password):
        """
        Initialize a new client, connecting to hecks with the given username and password.

        :param username: username to connect as
        :param password: password to use for connection
        """

        self._driver = webdriver.Firefox()
        self.connect(username, password)

    def connect(self, username, password):
        """
        Launch a web page to hecks and attempt to connect to given username and password.

        :param username: username to connect as
        :param password: password to use for connection
        """
        self._driver.get(HECKS_URL)
        if "login" not in self._driver.current_url:
            raise ClientError("Unable to reach login page. Are you already logged in?")

        # Find the fields and submit
        self._driver.find_element_by_id(USERNAME_FIELD_ID).send_keys(username)
        self._driver.find_element_by_id(PASSWORD_FIELD_ID).send_keys(password)
        self._driver.find_element_by_id(SUBMIT_BUTTON_ID).click()

    def execute_script(self, script):
        """ This just calls self._driver.run_script(script). Used for debugging. """
        self._driver.execute_script(json.dumps(script.strip().encode()))


class ClientError(Exception):
    pass


if __name__ == "__main__":
    client = HecksWebClient("asfffd", "asfffd")
