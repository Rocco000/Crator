from abc import ABC, abstractmethod

class CaptchaDetector(ABC):
    @abstractmethod
    def has_captcha(self, web_page: str) -> bool:
        """
        Detect if the given web page content contains a captcha.
        :param web_page: HTML content of the web page.
        :return: True if a captcha is detected, False otherwise.
        """
        pass