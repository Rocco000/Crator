from bs4 import BeautifulSoup

# Local import
from detectors import CaptchaDetector, WaitingPageDetector

class CocoricoCaptchaDetector(CaptchaDetector):
    def has_captcha(self, web_page: str) -> bool:
        return False

class CocoricoWaitingPageDetector(WaitingPageDetector):
    def is_waiting_page(self, web_page: str) -> bool:
        return False