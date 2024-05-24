from scrapers import DrughubScraper
from scrapers import Scraper

class Creator:
    """
    This class implement the Factory method design pattern to create the right scraper for the crawler
    """

    def create_scraper(self, website:str, product_category: str) -> Scraper:
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