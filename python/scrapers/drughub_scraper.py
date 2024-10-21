import re
from bs4 import BeautifulSoup

# Local import
from scrapers import Scraper

class DrughubScraper(Scraper):

    def extract_product_information(self, web_page) -> dict:
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")

        product_information = {
            "title": "",
            "description": "",
            "vendor": "",
            "origin": "",
            "destination": "",
            "currency": "",
            "price": 0.0,
            "cryptocurrency": "",
            "crypto_price": 0.0
        }

        # Extract the product title
        product_title_tag = soup.find("h1", class_="h2 m-0 mb-1")

        if product_title_tag:
            product_information["title"] = product_title_tag.get_text(strip=True)

        div_descriptor = soup.find("div", id="listing_description")

        # Extract the description
        if div_descriptor and len(div_descriptor.contents) == 1 and isinstance(div_descriptor.contents[0], str):
            x = div_descriptor.get_text(strip=True)

            # Replace 1 or more \n with whitespace
            x = re.sub(r"\n+", " ", x)

            # Replace one or more white space with only one white space
            product_information["description"] = re.sub(r"\s+", " ", x)

        # Extract vendor name
        for a_tag in soup.findAll("a"):
            href = a_tag.attrs.get("href")

            # Check whether the a tag is a vendor link
            if href and "vendor/" in href and len(a_tag.findAll()) == 0:
                product_information["vendor"] = a_tag.text.strip()
                break
        
        # Extract shipping information and price
        for div in soup.findAll("div", class_="col-auto"):
            div_text = div.get_text(" ",strip=True)

            match = re.search(r"Shipping from\s+(.+?)\s+to\s+(.+)", div_text)
            if match:
                product_information["origin"] = match.group(1)
                product_information["destination"] = match.group(2)

            # Extract price information
            match = re.search(r"Price \((\w+)\):\s*([\d.]+)", div_text)

            if match:
                currency = match.group(1)
                price = match.group(2)

                if "EUR" in currency or "USD" in currency or "GBP" in currency or "CHF" in currency or "CAD" in currency or "AUD" in currency or "NZD" in currency:
                    product_information["currency"] = currency
                    product_information["price"] = price
                else:
                    product_information["cryptocurrency"] = currency
                    product_information["crypto_price"] = price
        
        return product_information

    def check_image(self, class_value:str) -> bool:
        class_value = class_value.strip()
        if "img-thumbnail rounded m-0 p-0" in class_value:
            return True
        else:
            return False
        
    def check_category(self, web_page) -> bool:
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")

        for a_tag in soup.findAll("a", class_="p-0 m-0 text-decoration-none fs-4"):
            # Check if the a tag has only text as child and its value is the category of interest
            if len(a_tag.findAll()) == 0 and self.product_category in a_tag.text.strip().lower():
                return True
        
        return False