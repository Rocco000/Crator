from scrapers import Scraper
from scrapers import DrughubScraper, CocoricoScraper
from detectors import CaptchaDetector, WaitingPageDetector
from detectors import DrughubCaptchaDetector, DrughubWaitingPageDetector, CocoricoCaptchaDetector, CocoricoWaitingPageDetector
from extractors import BaseCookieExtractor, CocoricoCookieExtractor, DrughubCookieExtractor
from handler import TorHandler

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
            case "cocorico":
                return CocoricoScraper(product_category, product_micro_category)
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
            case "cocorico":
                return CocoricoCaptchaDetector()
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
            case "cocorico":
                return CocoricoWaitingPageDetector()
            case _:
                return None
            
    @staticmethod
    def create_cookie_extractor(tor_handler:TorHandler, homepage_url:str, seed:str, waiting_time:int, attempts:int, ) -> BaseCookieExtractor:
        """
        Create the right cookie extractor instance
        
        :param tor_handler:  an instance of TorHandler to handle HTTP requests
        :param homepage_url: the homepage url of the website to be crawled
        :param seed: the seed URL to be crawled
        :param waiting_time: the delay from two HTTP request
        :param attempts: number of attempts for the second HTTP request to obtain the session cookie
        :return: a cookie extractor
        """

        website = website.strip().lower()
        match website:
            case "drughub":
                return DrughubCookieExtractor(tor_handler, homepage_url, seed, waiting_time, attempts)
            case "cocorico":
                return CocoricoCookieExtractor(tor_handler, homepage_url, seed, waiting_time, attempts)
            case _:
                return None