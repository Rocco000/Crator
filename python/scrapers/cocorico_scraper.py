import re
from bs4 import BeautifulSoup
from bs4.element import Tag

#Local import
from scrapers import Scraper

class CocoricoScraper(Scraper):
    def __init__(self, product_category: str, product_micro_category: str):
        super().__init__(product_category, product_micro_category)

        self.product_shipping_map = dict()
        self.currency_mapping = {
            "$": "USD",      # United States Dollar
            "€": "EUR",      # Euro
            "£": "GBP",      # British Pound
            "C$": "CAD",     # Canadian Dollar
            "A$": "AUD",     # Australian Dollar
            "CHF": "CHF",    # Swiss Franc
        }

    def convert_currency_symbol(self, symbol: str) -> str:
        """
        Convert the currency symbol in its corresponding acronym
        :param symbol: the currency symbol
        """
        return self.currency_mapping.get(symbol)

    def extract_product_information(self, web_page) -> dict:
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser")

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

        # Extract product title, price and the vendor name
        div_tags = soup.findAll("div", class_="col-sm-4")
        for div in div_tags:
            # Check whether div contains a certain form
            product_form = div.findChild("form", class_="form-horizontal")
            if product_form:
                product_information["title"] = div.findChild("h1").text.strip() # Extract product TITLE 

                ul_tag = div.findChildren("ul", class_="list-unstyled")[1] # Get the second ul tag

                h2_text = ul_tag.findChild("h2").text.strip()
                match = re.search(r"(\d{1,3}(?:,\d{3})*\.\d+)([^\d\s]+)", h2_text) # Extract product PRICE
                if match:
                    product_information["price"] = match.group(1)
                    product_information["currency"] = self.convert_currency_symbol(match.group(2))
                
                # Get the vendor link
                vendor_a_tag = product_form.findChild("a")
                if vendor_a_tag:
                    href = vendor_a_tag.get("href")
                    if "seller" in href:
                        product_information["vendor"] = vendor_a_tag.text.strip() # Extract VENDOR NAME
                break
        
        # Extract description
        description_div = soup.find("div", id= "tab-description")

        if description_div:
            x = description_div.get_text(strip= True)

            # Replace 1 or more \n with whitespace
            x = re.sub(r"\n+", " ", x)

            # Replace one or more white space with only one white space
            product_information["description"] = re.sub(r"\s+", " ", x)
        
        # Get product shipping information web_page.url
        url = web_page.url
        url = url.replace("&amp;", "&")
        if url in self.product_shipping_map:
            product_information["origin"], product_information["destination"] = self.product_shipping_map[url].split(";")

            self.product_shipping_map.pop(url) # Remove the shipping information from dictionary
        
        return product_information
    
    def get_base_url(self, web_page_url: str) -> str:
        # Get all characters until .onion/store
        match = re.search(rf"(.*?{re.escape('.onion/store/nojs/')})", web_page_url)
        
        return match.group(1) if match else ""
        
    def get_url_category(self, url: str) -> str:
        match = re.search(r"(&path=\d+_\d+_\d+)", url)
        
        return match.group(0) if match else ""

    def check_image(self, img_tag: Tag) -> bool:
        # Get the immediate parents which is an <a> tag
        parent_a = img_tag.find_parent("a")

        if parent_a and parent_a.has_attr("class"):
            # Check class value
            class_list = parent_a["class"]
            return "thumbnail" in class_list
        else:
            return False


    def check_category(self, web_page) -> bool:
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser")
        
        ul_tag = soup.find("ul", class_= "breadcrumb")

        if ul_tag:
            children = ul_tag.findChildren("a") # Get all <a> children
            i = 0
            macro_flag = False
            micro_flag = False

            for child in children:
                # Jump the first two <a> tags (home -> drugs)
                if i > 1:
                    child_text = child.text.strip().lower() # Transform the string in lowercase

                    if child_text == self.product_category: # Check macro-category
                        macro_flag = True
                    elif self.product_micro_category in child_text: # Check micro-category
                        micro_flag = True
                
                i += 1

            # Check whether the current web page is a listing page
            if len(children) < 5:
                div_micro_category = soup.find("div", id= "content") # Get the <div> tag which contains the micro-category
                
                if div_micro_category:
                    # Get the first <h2> child
                    h2_text = div_micro_category.findChild("h2").text.strip().lower()

                    if self.product_micro_category in h2_text:
                        # Extract product shipping information
                        self.store_product_shipping_information(web_page)
                    else:
                        return False
            
            return macro_flag and micro_flag
        else:
            return False

    def store_product_shipping_information(self, web_page) -> None:
        """
        Store the product shipping information ina dictionary {url: shipping information}
        :param web_page: the current web page
        """
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser")

        caption_divs = soup.findAll("div", class_= "caption")
        image_divs = soup.findAll("div", class_= "image")

        for c_div, i_div in zip(caption_divs, image_divs):
            shipping_info = c_div.findAll("center", recursive=False)[1] # Get the second <center> tag
            
            origin, destination = shipping_info.get_text(separator="\n").split("\n")

            # Remove the initial emoticon
            origin = re.sub(r"^[^\w\s]+:", "", origin)
            destination = re.sub(r"^[^\w\s]+:", "", destination)

            a_tag = i_div.find("a")["href"]

            if not a_tag:
                continue
            
            a_tag = a_tag.replace("&amp;", "&")
            self.product_shipping_map[a_tag] = f"{origin}; {destination}"