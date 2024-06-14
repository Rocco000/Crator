from scrapers import DrughubScraper
from scrapers import Scraper
from detectors import CaptchaDetector, DrughubCaptchaDetector

class Creator:
    """
    This class implements the Factory method design pattern to create the correct scraper and captcha detector for the crawler.
    """

    @staticmethod
    def create_scraper(website:str, product_category: str) -> Scraper:
        """
        Returns the right scraper based on website parameter
        :param website: website name on which you want to extract data
        :return: a subclass of Scraper
        """
        website = website.strip().lower()
        match website:
            case "drughub":
                return DrughubScraper(product_category)
            case _:
                return None
    
    @staticmethod
    def create_captcha_detctor(website:str) -> CaptchaDetector:
        """
        Returns the right captcha detector based on the website name
        :param website: website name
        :return: a subclass of CaptchaDetector
        """

        website = website.strip().lower()
        match website:
            case "drughub":
                return DrughubCaptchaDetector()
            case _:
                return None

