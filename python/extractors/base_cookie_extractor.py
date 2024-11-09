from abc import ABC, abstractmethod

# Local imports
from utils.config import Configuration
from handler import TorHandler

class BaseCookieExtractor(ABC):
    """
    Abstract base class for extracting cookies from websites using the Tor network.

    This class defines a general interface for extracting session cookies from a target website.
    It uses a TorHandler instance to send HTTP requests through Tor.
    """

    def __init__(self, tor_handler: TorHandler, homepage_url: str, seed: str, waiting_time=5, attempts=3):
        """
        Initializes the BaseCookieExtractor

        :param tor_handler:  an instance of TorHandler to handle HTTP requests
        :param homepage_url: the homepage URL of the website to extract cookies from
        :param seed: the seed URL from which the crawler starts
        :param waiting_time: time delay (in seconds) between requests.
        :param attempts: maximum number of attempts to extract cookies.
        """
        self.tor_handler = tor_handler
        self.homepage_url = homepage_url
        self.seed = seed
        self.waiting_time = waiting_time
        self.attempts = attempts

    @abstractmethod
    def get_new_cookie(self) -> str:
        """
        Abstract method to obtain a new session cookie.

        This method should be implemented by subclasses to define website-specific logic for obtaining cookies.
        :return: A string containing the session cookie if successful, otherwise None.
        """
        pass

    def store_new_cookie(self, config: Configuration):
        """
        Store a new cookie in the YAML file
        :param config: an instance of Configuration class to handle the YAML file
        :return: True whether get_new_cookie() returns a new cookie, False otherwise
        """
        cookies = self.get_new_cookie()
        if cookies:
            config.add_cookie(self.seed, cookies) # Store the new cookie in the YAML file
            print("Added a new cookie!")

            # Restart Tor to get another IP address and, therefore a new identity
            self.tor_handler.renew_connection() 
            return True
        return False
    
    def stop(self) -> None:
        """
        Stop the Tor process.
        """
        self.tor_handler.stop_tor_process()