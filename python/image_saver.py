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

# Local imports
import utils.fileutils as file_utils
from handler import TorHandler


logger = logging.getLogger("CRATOR")

class ImageSaver:
    def __init__(self, website, save_path, image_mapping_path, macro_category, micro_category,tor_handler:TorHandler, base64_flag:bool=True, n_threads=1):
        """
        :param website: website name
        :param save_path: the file path to store the images
        :param image_mapping_path: the file path of the csv file to store the mapping between images and urls
        :param macro_category: macro category of the drugs
        :param micro_category: micro category of the drugs
        :param tor_handler: an instance of TorHandler to make an http request
        :param flag_relative_url: True if the image url are relative url, False otherwise
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

    def get_image_extension(self, content_type) -> str:
        """
        Provides the image extension
        :param content_type: the content type of the http response
        :return image extension as string
        """
        if self.base64_flag:
            if "jpg" in content_type:
                return ".jpg"
            elif "jpeg" in content_type:
                return ".jpeg"
            elif "png" in content_type:
                return ".png"
            else:
                print(f"The src content encoded in base64 isn't an image.")
                return None
        else:
            if content_type.startswith('image/jpeg'):
                return ".jpeg"
            elif content_type.startswith('image/jpg'):
                return ".jpg"
            elif content_type.startswith('image/png'):
                return ".png"
            else:
                print(f"The response content type isn't an image. It is {content_type}")
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
                        if not self.base64_flag:
                            img_url = None
                            # Check if src_tag has a relative path
                            if not bool(urlparse(src_tag).netloc):
                                img_url = urljoin(url, src_tag)
                            else:
                                img_url = src_tag
                            
                            #Send request to obtain the image
                            img_response = self.tor_handler.send_request(img_url, cookie)

                            # Check if the request was successful
                            if img_response.status_code == 200:
                                print("Response status code is 200, success")
                                response_content_type = img_response.headers.get('content-type')
                                print(f"content-type: {response_content_type}")

                                image_data = BytesIO(img_response.content)
                            else:
                                print(f"Error {img_response.status_code} occured during the download of the image for the following url: {url}")
                                logger.error(f"IMAGE SAVER - Error {img_response.status_code} occured during the download of the image for the following url: {url}")
                        else:
                            try:
                                # Decode the base64 encoding
                                image_data = base64.b64decode(src_tag.split(',')[1])
                            except IndexError:
                                logger.error(f"IMAGE SAVER - Unable to split src_tag -> {src_tag}")
                                continue
                            except AttributeError:
                                logger.error(f"IMAGE SAVER - src_tag has no split method -> {src_tag}")
                                continue
                            except Exception:
                                logger.error(f"IMAGE SAVER - Exception occured during the decoding of the image -> {src_tag}")
                                continue

                        # Get the image extension
                        extension = self.get_image_extension(src_tag)

                        if extension is None:
                            print(f"Unable to download the image ({src_tag}), it has a different extension")
                            logger.info(f"Unable to download the image ({src_tag}), it has a different extension")
                            continue
                        
                        """scelta = bool(input("Do you want to show the image before store it?\n"))
                        if scelta:
                            try:
                                # Open image using PIL
                                print("Show the image")
                                img = Image.open(BytesIO(image_decoded))
                                
                                # Display image
                                img.show()
                                img.close()
                            except Exception as e:
                                print("Error occurred while displaying the image:")
                                print(traceback.format_exc())"""

                        file_name = f"image{count}_{depth_node}_{index_node}{extension}"
                        dir = os.path.join(self.save_path, file_name)

                        try:
                            # Store the image
                            print("Saving the image...")
                            executor.submit(file_utils.save_image, image_data, dir)

                            # Store the mapping image - url
                            with open(self.image_mapping_file, "a") as csvfile:
                                print("Updating the csv file")
                                csv_writer = csv.writer(csvfile)
                                csv_writer.writerow([self.website, file_name, str(index_node)+".html", url, depth_node, index_node, product_information["title"], product_information["description"], product_information["vendor"], product_information["origin"], product_information["destination"], product_information["currency"], product_information["price"], product_information["cryptocurrency"], product_information["crypto_price"], self.macro_category, self.micro_category])
                            time.sleep(0.1)
                        except TimeoutError:
                            logger.info(f"IMAGE SAVER - Timeout occurred while saving image: {file_name}")

                            # Re-insert the image in the queue to retry to save it
                            self.enqueue(src_tag, url, index_node, depth_node, cookie, count)
                        except Exception as e:
                            logger.error(f"IMAGE SAVER - Error occured while saving the image: {e}")