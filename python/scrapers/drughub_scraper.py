import re
from bs4 import BeautifulSoup

# Local import
from scrapers import Scraper

class DrughubScraper(Scraper):

    def extract_product_information(self, web_page) -> dict:
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")

        product_information = {
            "description": "",
            "vendor": "",
            "origin": "",
            "destination": "",
            "currency": "",
            "price": 0.0,
            "cryptocurrency": "",
            "crypto_price": 0.0
        }

        div_descriptor = soup.find("div", id="listing_description")

        # Extract the description
        if div_descriptor and len(div_descriptor.contents) == 1 and isinstance(div_descriptor.contents[0], str):
            # replace() to remove \n
            x = div_descriptor.get_text(strip=True).replace("\n", " ")
            # Replace one or more white space with only one white space
            product_information["description"] = re.sub(r"\s+", " ", x)

        # Extract vendor name
        for a_tag in soup.findAll("a"):
            href = a_tag.attrs.get("href")

            # Check whether the a tag is a vendor link
            if href and "vendor/" in href and len(a_tag.findAll()) == 0:
                product_information["vendor"] = a_tag.text.strip()
                break
        
        # Extract product location and price
        for div in soup.findAll("div"):
            children = list(div.children)
            div_text = div.get_text()

            if len(children) == 5 and "Shipping from" in div_text:

                # Regex to extract the two locations
                pattern_location = r'from\s+(\w+)\s+to\s+(\w+)'
                match = re.search(pattern_location, div_text)

                if match:
                    product_information["origin"] = match.group(1)
                    product_information["destination"] = match.group(2)
            elif len(children) == 3 and "Price" in div_text:

                # Check whether the price is a monetary or cryptocurrency price
                if "EUR" in div_text or "USD" in div_text or "GBP" in div_text or "CHF" in div_text or "CAD" in div_text or "AUD" in div_text or "NZD" in div_text:
                    
                    # Regex to extract the currency
                    pattern_currency = r'\((.*?)\)'
                    matches = re.findall(pattern_currency, div_text)
                    if matches:
                        product_information["currency"] = matches[0]

                    # Regex to extract the price
                    pattern_price = r'\b\d+\.\d+\b'
                    matches = re.findall(pattern_price, div_text)
                    if matches:
                        product_information["price"] = float(matches[0])
                else:
                    
                    # Regex to extract the crypto currency
                    pattern_crypto_currency = r'\((.*?)\)'
                    matches = re.findall(pattern_crypto_currency, div_text)
                    if matches:
                        product_information["cryptocurrency"] = matches[0]

                    # Regex to extract the price
                    pattern_price = r'\b\d+\.\d+\b'
                    matches = re.findall(pattern_price, div_text)

                    if matches:
                        product_information["crypto_price"] = float(matches[0])
        
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

        for a_tag in soup.findAll("a"):
            # Check if the a tag has only text as child and its value is the category of interest
            if len(a_tag.findAll()) == 0 and self.product_category in a_tag.text.strip().lower():
                return True
        
        return False