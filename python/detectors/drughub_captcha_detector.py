from bs4 import BeautifulSoup

# Local import
from detectors import CaptchaDetector

class DrughubCaptchaDetector(CaptchaDetector):

    def has_captcha(self, web_page: str) -> bool:
        # Make soup
        soup = BeautifulSoup(web_page, "html.parser", from_encoding="iso-8859-1")

        # Get the web page title
        title_content = soup.title.string
        title_content = title_content.lower()

        return "captcha" in title_content

