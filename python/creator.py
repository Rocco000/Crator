from scrapers import DrughubScraper
from scrapers import Scraper
from detectors import CaptchaDetector, WaitingPageDetector, DrughubCaptchaDetector, DrughubWaitingPageDetector

class Creator:
    """
    This class implements the Factory method design pattern to create the correct scraper and captcha detector for the crawler.
    """

    @staticmethod
    def create_scraper(website: str, product_category: str, product_micro_category: str) -> Scraper:
        """
        Return a subclass of Scraper based on website parameter.
        :param website: website name on which to extract data.
        :param product_category: product category to be scraped.
        :param product_micro_category: product micro-category to be scrape.
        :return: a subclass of Scraper
        """
        website = website.strip().lower()
        match website:
            case "drughub":
                return DrughubScraper(product_category, product_micro_category)
            case _:
                return None
    
    @staticmethod
    def create_captcha_detector(website: str) -> CaptchaDetector:
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
            
    @staticmethod
    def create_waiting_page_detector(website: str) -> WaitingPageDetector:
        """
        Return the right waiting page detector based on the website name.
        :param website: website name
        :return: a subclass of WaitingPageDetector
        """

        website = website.strip().lower()
        match website:
            case "drughub":
                return DrughubWaitingPageDetector()
            case _:
                return None