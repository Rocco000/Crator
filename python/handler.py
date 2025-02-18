import time
import requests
import threading
import logging
import random
from fake_useragent import UserAgent
from stem.control import Controller
from stem import Signal
from urllib.parse import urlparse
import psutil
import subprocess
import re

from http.cookies import SimpleCookie

# Local imports
from utils.config import Configuration
import detector
from exceptions import InvalidCookieException, HTTPStatusCodeError
from detectors import CaptchaDetector

logger = logging.getLogger("CRATOR")
MAX_CONNECTION_ATTEMPT = 3
NEW_REQUEST_DELAY = 2


class TorHandler:
    def __init__(self, tor_password:str, tor_port:int, proxy:str, venv_path:str):
        """
        :param tor_password: the password required to authenticate with the Tor control port. It should match the
        hashed password set in the Tor configuration file (torrc).
        :param tor_port: the port number on which the Tor control port is listening. 
        :param proxy: the HTTP proxy address to route traffic through Tor. This should be in the format 'socks5h://127.0.0.1:PORT', where PORT
        corresponds to the SOCKS port on which the Tor instance is listening.
        :param venv_path: the path to the python virtual environment
        """
        print("TorHandler init")
        self.proxy = {"http": proxy, "https": proxy}
        self.lock = threading.Lock()

        self.n_requests_sent = 0
        self.tor_password = tor_password
        self.tor_port = tor_port
        self.venv_path = venv_path

        # Get the socks port
        pattern_socks_port = r".*:(\d+)"
        match = re.search(pattern_socks_port, proxy)

        self.socks_port = 0
        if match:
            self.socks_port = match.group(1)
        else:
            print("No socks port found!")

    def get_random_useragent(self) -> str:
        """
        Gets a random user agent string.

        :return: A random user agent string.
        """
        ua = UserAgent()
        return ua.random

    def send_request(self, url:str, cookie:str =None):
        """
        Sends an HTTP request to obtain a web page.

        :param url: the URL to send an HTTP request to
        :param cookie: the cookie value to use in the HTTP header
        :return: the web page pointed at by the given URL and the used cookie.
        """
        if self.lock.locked():
            logger.debug("TOR HANDLER - Waiting for a new ip.")
        while self.lock.locked():
            time.sleep(1)

        # attempt = 0
        # web_page = None
        # status_code = 200

        logger.debug(f"TOR HANDLER - Downloading URL: {url}")

        header = {'User-Agent': self.get_random_useragent()}
        if cookie:
            header["Cookie"] = cookie

        web_page = requests.get(url, headers=header, proxies=self.proxy)
        status_code = web_page.status_code
        logger.debug(f"TOR HANDLER - STATUS CODE: {status_code}")
        self.n_requests_sent += 1

        # while not web_page and attempt < MAX_CONNECTION_ATTEMPT:
        #
        #
        #     # Check if the request has been succeeded
        #     if not(200 <= status_code < 300):
        #         logger.debug(f"TOR HANDLER - Status code {status_code}. New request attempt in {NEW_REQUEST_DELAY}s")
        #         status_code = web_page.status_code
        #         web_page = None
        #         attempt += 1
        #         time.sleep(NEW_REQUEST_DELAY)

        # if attempt >= MAX_CONNECTION_ATTEMPT:
        #     raise HTTPStatusCodeError(status_code)

        return web_page, cookie

    def is_url_reachable(self, url, cookie=None) -> bool:
        """
        Check if a url is reachable
        :param url: the url to analyze. It can be with or without scheme
        :param cookie: a valid cookie session
        :return: true if a url is reachable, false otherwise.
        """
        # Check schema: if no schema ahs been found, set an http schema
        logger.debug(f"TOR HANDLER - URL CHECK: {url}")

        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            url = "http://" + url

        try:
            self.send_request(url, cookie=cookie)
            logger.debug(f"TOR HANDLER - URL CHECK: TRUE")
            return True
        except ConnectionError:
            pass

        logger.debug(f"TOR HANDLER - URL CHECK: FALSE")
        return False

    def renew_connection(self) -> None:
        """
        Restarts Tor to change the IP address.
        :return: None
        """
        with self.lock:
            logger.debug(f"{type(self).__name__} - New ip generation...")
            header = {'User-Agent': self.get_random_useragent()}
            try:
                ip = requests.get('https://api.ipify.org', proxies=self.proxy, headers=header).text.strip()

                logger.debug(f"{type(self).__name__}  - Actual IP: {ip}")

                # Send a request to Tor asking for a new IP address
                with Controller.from_port(port=self.tor_port) as controller:
                    controller.authenticate(self.tor_password)
                    controller.signal(Signal.NEWNYM)

                time.sleep(10)  # Ensure Tor has time to establish a new circuit

                # Check if the IP address has been changed
                new_ip = self.get_ip()
                while new_ip == ip:
                    time.sleep(1)
                    new_ip = self.get_ip()

                logger.debug(f"{type(self).__name__}  - New IP: {new_ip}")
            except Exception as e:
                logger.error(f"Error during IP renewal: {e}")
    

    def get_ip(self) -> str:
        """
        Returns the current IP address.
        :return: the actual IP address.
        """
        header = {'User-Agent': self.get_random_useragent()}
        return requests.get('https://api.ipify.org', proxies=self.proxy, headers=header).text.strip()

    def stop_tor_process(self) -> None:
        """
        Stop a Tor process listening on any of the specified ports.
        """
        try:
            subprocess.run(['sudo', self.venv_path, 'python/utils/tor_process_handler.py', str(self.tor_port), str(self.socks_port)])
        except psutil.AccessDenied:
            print(f"{type(self).__name__} - Access denied - Insufficient permissions to access the process.")
            logger.error(f"{type(self).__name__} - Access denied - Insufficient permissions to access the process.")
        except psutil.ZombieProcess:
            print(f"{type(self).__name__} - Zombie process - Process has already terminated but not yet cleaned up.")
            logger.error(f"{type(self).__name__} - Zombie process - Process has already terminated but not yet cleaned up.")
        except psutil.NoSuchProcess:
            print(f"{type(self).__name__} - No such process - It might have been terminated already.")
            logger.error(f"{type(self).__name__} - No such process - It might have been terminated already.")
        except TypeError as e:
            print(f"{e}")
            logger.error(f"{type(self).__name__} - {e}")

class CookieHandler:
    def __init__(self, seed, torhandler:TorHandler, captcha_detector:CaptchaDetector):
        """
        :param seed: the URL to be cralwed
        :param torhandler: an instance of TorHandler
        :param captcha_detector: an instanca of CaptchaDetector
        """
        print("CookieHandler init")
        self.config = Configuration()

        self.seed = seed
        self.tor_handler = torhandler
        self.nocookiepage = None

        self.bucket_cookies = None
        self.cookies = None

        self.captcha_detector = captcha_detector

    @property
    def nocookiepage(self):
        return self._nocookiepage

    @nocookiepage.setter
    def nocookiepage(self, page):
        self._nocookiepage = page

    def is_valid(self, url:str, cookie:str) -> bool:
        """
        Checks if the cookie is valid or not.

        :param url: the url to send an HTTP request to check the cookie's validity.
        :param cookie: the cookie value to check its validity.
        :return: True if the cookie is valid, False otherwise.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            url = "http://" + url

        try:
            web_page, _ = self.tor_handler.send_request(url, cookie)
            if self.nocookiepage and detector.login_redirection(web_page, self.nocookiepage):
                logger.info(f"{self.seed} COOKIE HANDLER - Validity CHECK: False -> Login redirection")
                return False
            if self.captcha_detector.has_captcha(web_page.content) or detector.captcha_detector(url, web_page):
                logger.info(f"{self.seed} COOKIE HANDLER - Validity CHECK: False -> Captcha")
                return False
        except Exception as e:
            logger.error(f"{self.seed} COOKIE HANDLER - Error msg: {str(e)}")
            return False

        return True

    def cookies_validity_check(self, url:str) -> None:
        """
        Checks whether the cookies stored in the YAML file for the self.seed are still valid, otherwise, deletes them if they are not.

        :param url: the url to send an HTTP request to check the cookie's validity.
        :return: None
        """
        print("\nCOOKIE HANDLER - Cookies validity check\n")
        logger.info(f"{self.seed} COOKIE HANDLER - Cookies validity check ")
        if not self.cookies or self.config.is_updated():
            try:
                self.cookies = self.config.cookies(self.seed)
                # self.cookies = market_config.get_cookies(self.market)
            except:
                error_msg = "No cookies found in the market config file"
                logger.error(f"{self.seed} COOKIE HANDLER - {error_msg}")
                print(f"in coockies_validity_check(): {self.seed} COOKIE HANDLER - {error_msg}")
                raise FileNotFoundError(error_msg)

        if not self.cookies:
            error_msg = "Empty list in the market config file. Please update it with at least one valid cookie."
            logger.error(f"{self.seed} COOKIE HANDLER - {error_msg}")
            raise InvalidCookieException(error_msg)

        for cookie in self.cookies:
            logger.info(f"{self.seed} - Cookie validity check")
            logger.info(f"{self.seed} - Cookie: {cookie}")

            if not self.is_valid(url, cookie):
                logger.info(f"{self.seed} - INVALID COOKIE")
                self.remove_cookie(cookie)
            else:
                logger.info(f"{self.seed} - VALID COOKIE")

    def get_random_cookie(self, url:str, validity_check:bool =True) -> str:
        """
        Gets a random cookie from the bucket to use for an HTTP request.

        :param url: the URL to send an HTTP request to, requiring a cookie.
        :param validity_check: the flag indicating whether or not to check the validity of the cookie.
        :return: a random cookie from the bucket, None otherwise.
        """
        # Check if there are cookies in the cookie list. If not, read them from the market config file.
        if not self.cookies or self.config.is_updated():
            try:
                self.cookies = self.config.cookies(self.seed)
                # self.cookies = market_config.get_cookies(self.market)
                if not self.cookies:
                    # raise InvalidCookieException("Empty list in the market config file. "
                    #                              "Please update it with at least one valid cookie.")
                    return None
            except:
                raise FileNotFoundError("No cookies found in the market config file")

        # Bucket cookies list is empty because all the cookies have already been chosen.
        # Replenish the bucket with the cookies saved in the market config file
        if not self.bucket_cookies:
            self.bucket_cookies = self.cookies.copy()

        logger.debug(f"{self.seed} COOKIE HANDLER - RANDOM COOKIE -> COOKIE LIST")
        [logger.debug(f"{self.seed} - {ck}") for ck in self.cookies]
        logger.debug(f"{self.seed} COOKIE HANDLER - RANDOM COOKIE -> BUCKET COOKIE LIST")
        [logger.debug(f"{self.seed} - {ck}") for ck in self.bucket_cookies]

        if not validity_check:
            random_index = random.randint(0, len(self.bucket_cookies) - 1)  # generate a random index
            return self.bucket_cookies.pop(random_index)  # remove the element at the random index

        # Cookie validity check
        while self.bucket_cookies:
            random_index = random.randint(0, len(self.bucket_cookies) - 1)  # generate a random index
            random_cookie = self.bucket_cookies.pop(random_index)  # remove the element at the random index

            logger.debug(f"{self.seed} COOKIE HANDLER - RANDOM COOKIE -> BUCKET COOKIE LIST (UPDATE)")
            [logger.debug(f"{self.seed} - {ck}") for ck in self.bucket_cookies]

            if self.is_valid(url, random_cookie):
                return random_cookie
            else:
                # Remove the invalid cookie from the list and in the market config file
                self.remove_cookie(random_cookie)

            if not self.bucket_cookies:
                self.bucket_cookies = self.cookies.copy()

        return None

    def remove_cookie(self, cookie:str) -> None:
        """
        Remove the cookie from the list and in the market config file
        :param cookie: the cookie to be removed.
        :return: None
        """
        try:
            logger.debug(f"{self.seed} - REMOVE COOKIE")
            logger.debug(f"{self.seed} - COOKIE LIST")
            [logger.debug(f"{self.seed} - BEFORE: {cookie}") for cookie in self.cookies]
            self.cookies.remove(cookie)
            [logger.debug(f"{self.seed} - AFTER: {cookie}") for cookie in self.cookies]

            self.config.remove_cookie(self.seed, cookie)
            # market_config.remove_cookie(self.market, cookie)
        except ValueError as ve:
            logger.error(f"{self.seed} - COOKIE TO REMOVE NOT FOUND.")
            logger.error(f"{self.seed} - Error msg: {str(ve)}.")


if __name__ == '__main__':
    handler = TorHandler("abc", 9051, "socks5h://localhost:9050", "/home/rocco/Desktop/jads_project/Crator/.venv/bin/python")
    handler.stop_tor_process()
