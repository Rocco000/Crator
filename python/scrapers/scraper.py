from abc import ABC, abstractmethod
from bs4.element import Tag

class Scraper(ABC):

    def __init__(self, product_category: str, product_micro_category: str):
        """
        :param product_category: product category to be scraped.
        :param product_micro_category: product micro-category to be scraped.
        """
        self.product_category = product_category
        self.product_micro_category = product_micro_category

    @abstractmethod
    def extract_product_information(self, web_page) -> dict:
        """
        Extracts all the necessary product information (vendor name, price, etc)
        :param web_page: the product web page
        :return: a dictionary containing all product information.
        """
        pass

    @abstractmethod
    def get_base_url(self, web_page_url: str) -> str:
        """
        Extract the base URL from the given URL
        :param web_page_url: the url of the visited web page
        """
        pass

    @abstractmethod
    def get_url_category(self, url: str) -> str:
        """
        Return the product category expressed in the URL
        :param url: the url of the website being crawled
        :return: product category expressed in the URL
        """
        pass

    @abstractmethod
    def check_image(self, img_tag: Tag) -> bool:
        """
        Checks the validity of the image's class attribute
        :param img_tag: a <img> tag extracted from the current web page
        :return: True if the class attribute is correct, False otherwise
        """
        pass

    @abstractmethod
    def check_category(self, web_page) -> bool:
        """
        Checks the products category of the current web page.
        :param web_page: the current web page
        :return: It returns true if the category is the same of the yaml file, false otherwise
        """
        pass