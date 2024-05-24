from abc import ABC, abstractmethod

class Scraper(ABC):

    def __init__(self, product_category):
        self.product_category = product_category

    @abstractmethod
    def extract_product_information(self, web_page) -> dict:
        """
        Extracts all the necessary product information (vendor name, price, etc)
        :param web_page: the product web page
        :return: a dictionary containing all product information.
        """
        pass

    @abstractmethod
    def check_image(self, class_value:str) -> bool:
        """
        Checks the validity of the image's class attribute
        :param class_value: value of the image's class attribute
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