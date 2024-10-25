from abc import ABC, abstractmethod

class CaptchaDetector(ABC):
    @abstractmethod
    def has_captcha(self, web_page: str) -> bool:
        """
        Detect whether the given web page content contains a captcha.
        :param web_page: HTML content of the web page.
        :return: True if a captcha is detected, False otherwise.
        """
        pass

class WaitingPageDetector(ABC):
    @abstractmethod
    def is_waiting_page(self, web_page: str) -> bool:
        """
        Detect whether the given web page is a waiting page.
        :param web_page: HTML content of the web page.
        :return: True if a waiting page is detected, False otherwise.
        """
        pass