import threading
import time
import os
import csv
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from PIL import Image
from io import BytesIO
import traceback
import base64 # To decode the images in base64
import logging
import requests

# Local imports
from scrapers.cocorico_scraper import CocoricoScraper
import utils.fileutils as file_utils
from handler import TorHandler
from scrapers import Scraper


logger = logging.getLogger("CRATOR")

class ImageSaver:
    def __init__(self, website, save_path, image_mapping_path, macro_category, micro_category, scraper: Scraper, tor_handler:TorHandler, base64_flag:bool, n_threads=1):
        """
        :param website: website name
        :param save_path: the file path to store the images
        :param image_mapping_path: the file path of the csv file to store the mapping between images and urls
        :param macro_category: drugs macro-category
        :param micro_category: drugs micro-category
        :param scraper: an instance of Scraper class
        :param tor_handler: an instance of TorHandler to make an HTTP request
        :param base64_flag: True if images are encoded in base64, False otherwise
        """
        self.n_threads = n_threads
        self.save_path = save_path
        self.image_mapping_file = image_mapping_path
        self.macro_category = macro_category
        self.micro_category = micro_category
        self.website = website

        self.queue = deque()
        self.lock = threading.Lock()
        self.running = True
        self.tor_handler = tor_handler
        self.base64_flag = base64_flag
        self.scraper = scraper

    def enqueue(self, src_image, url, index_node:int, depth_node:int, cookie, count:int, product_information:dict) -> None:
        """
        Stores the parameters in a queue as a tuple
        :param src_image: url of the img tag
        :param url: web page url
        :param index_node: web page index in the graph
        :param depth_node: web page depth level in the graph
        :param cookie: cookie to make a http request
        :param count: image number
        :param product_information: a dictionary containing all the necessary information on drug item
        """
        #print("Aggiunto foto da salvare")
        self.queue.append((src_image, url, index_node, depth_node, cookie, count, product_information))

    def is_empty(self) -> bool:
        """
        :return: True if the queue is not empty, False otherwise
        """
        return not self.queue

    def stop(self) -> None:
        self.running = False

    def start(self) -> None:
        threading.Thread(target=self.save, daemon=True).start()

    def get_image_extension(self, src_value) -> str:
        """
        Provides the image extension
        :param src_value: the src attribute content of the <img> tag
        :return: image extension as string
        """
        
        if "jpg" in src_value:
            return ".jpg"
        elif "jpeg" in src_value:
            return ".jpeg"
        elif "png" in src_value:
            return ".png"
        else:
            logger.error(f"IMAGE SAVER - The element {src_value} is not an image!")
            return None

    def download_base64_image(self, src_value: str):
        """
        Download an image encoded in base64.
        
        :param src_value: the src attribute content of the <img> tag
        :return: the decoded image
        """
        try:
            # Decode the base64 encoding
            image_data = base64.b64decode(src_value.split(',')[1])
            return image_data
        except IndexError:
            logger.error(f"IMAGE SAVER - Unable to split src_value -> {src_value}")
            return None
        except AttributeError:
            logger.error(f"IMAGE SAVER - src_value has no split method -> {src_value}")
            return None
        except Exception:
            logger.error(f"IMAGE SAVER - Exception occured during the decoding of the image -> {src_value}")
            return None

    def download_url_image(self, web_page_url: str, img_url: str, cookie: str) -> bytes:
        """
        Download an image using its URL
        
        :param web_page_url: the URL of the web page containing the image
        :param img_url: the src attribute content of the <img> tag
        :param cookie: a cookie to be use in the HTTP request
        :return: the image content in bytes
        """
        
        # Extract the base URL from the web page URL
        base_url = self.scraper.get_base_url(web_page_url)

        # Resolve the relative path whether img_url has a relative path
        full_img_url = urljoin(base_url, img_url) if not bool(urlparse(img_url).netloc) else img_url

        # Send an HTTP request to obtain the image
        try:
            img_response, _ = self.tor_handler.send_request(full_img_url, cookie)

            response_content_type = img_response.headers.get('content-type')
            print(f"content-type: {response_content_type}")

            return BytesIO(img_response.content).getvalue()
        except requests.exceptions.HTTPError as e:
            # To handle HTTP errors (4xx to 5xx)
            print(f"HTTP error {e.response.status_code} for URL: {full_img_url}")
            logger.error(f"HTTP error {e.response.status_code} for URL: {full_img_url}")
            return None
        except requests.exceptions.RequestException as e:
            # To handle other types of request-related errors
            print(f"IMAGE SAVER - Error occurred: {e} . For URL: {full_img_url}")
            logger.error(f"IMAGE SAVER - Error occurred: {e} . For URL: {full_img_url}")
            return None

    def save(self) -> None:
        """
        Stores the images in self.save_path and update a csv file to store the items information and the mapping between images and the website
        """
        with ThreadPoolExecutor(max_workers=self.n_threads) as executor:
            while self.running:
                # Wait whether the queue is empty 
                if not self.queue:
                    time.sleep(0.1)
                    continue

                with self.lock:
                    while self.queue:
                        # Get item from the queue
                        src_tag, url, index_node, depth_node, cookie, count, product_information = self.queue.popleft()
                        image_data = None
                        
                        # Check whether the src content is encoded in base64 
                        if self.base64_flag:
                            image_data = self.download_base64_image(src_tag)
                        else:
                            image_data = self.download_url_image(url, src_tag, cookie)

                        # Skip processing if download failed
                        if image_data is None:
                            print(f"IMAGE SAVER - Unable to download the image {src_tag}")
                            logger.error(f"IMAGE SAVER - Unable to download the image {src_tag}")
                            continue

                        # Get the image extension
                        extension = self.get_image_extension(src_tag)

                        if extension is None:
                            print(f"IMAGE SAVER - Unable to download the image ({src_tag}), it has a different extension")
                            logger.error(f"IMAGE SAVER - Unable to download the image ({src_tag}), it has a different extension")
                            continue

                        file_name = f"image{count}_{depth_node}_{index_node}{extension}"
                        dir = os.path.join(self.save_path, file_name)

                        try:
                            # Store the image
                            print("Saving the image...")
                            executor.submit(file_utils.save_image, image_data, dir)

                            # Store the mapping image - url
                            with open(self.image_mapping_file, mode="a", newline='', encoding="utf-8") as csvfile:
                                print("Updating the csv file")
                                csv_writer = csv.writer(csvfile, quotechar='"', quoting=csv.QUOTE_MINIMAL)
                                csv_writer.writerow([self.website, file_name, str(index_node)+".html", url, depth_node, index_node, product_information["title"], product_information["description"], product_information["vendor"], product_information["origin"], product_information["destination"], product_information["currency"], product_information["price"], product_information["cryptocurrency"], product_information["crypto_price"], self.macro_category, self.micro_category])
                            time.sleep(0.1)
                        except TimeoutError:
                            logger.info(f"IMAGE SAVER - Timeout occurred while saving image: {file_name}")

                            # Re-insert the image in the queue to retry to save it
                            self.enqueue(src_tag, url, index_node, depth_node, cookie, count)
                        except Exception as e:
                            logger.error(f"IMAGE SAVER - Error occured while saving the image: {e}")