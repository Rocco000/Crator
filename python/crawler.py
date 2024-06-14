import random
import logging
import sys
import time
from datetime import datetime
import hashlib
from waiting import wait
from waiting.exceptions import TimeoutExpired
import os
from collections import deque
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import re

# Local imports
from handler import TorHandler, CookieHandler, TorCookiesHandler
from monitor import CrawlerMonitor
from detector import captcha_detector, login_redirection
from downloader import Downloader
from saver import FileSaver
from image_saver import ImageSaver
from creator import Creator
from utils.config import Configuration
import utils.fileutils as file_utils
from exceptions import InvalidURLException, HTTPStatusCodeError

MAX_RETRIES = 3
MAX_COOKING_WAITING_TIME = 36000     # 10 hours

logger = logging.getLogger("CRATOR")


class Crawler:
    """
    Crawler for tor onion links
    """
    def __init__(self, seed, tor_handler=None, crator_config_path=None, project_path=None):
        """
        Initialize the class crawler
        :param seed: the url to crawl
        :param tor_handler: an instance of the TorHandler class, useful when the crawler is executed in a multithread
        environment and the tor requests must be shared among the threads (e.g., if a webpage contains
        a captcha, the handler requests a new ip, blocking all the connections until the new ip.
        """
        print("Crawler init")
        self.config = Configuration(crator_config_path)
        self.max_link = self.config.max_links()
        self.max_crawl_time = self.config.max_time()
        self.max_depth = self.config.depth()
        self.wait_request = int(self.config.wait_request()) / 1000
        self.max_retries = 5
        self.retries_counter = 0
        self.max_retries_before_renew = 5
        self.check_cookie = self.config.check_cookie()

        self.seed = seed
        self.login_page = None
        self.retry_queue = {}

        self.tor_handler = tor_handler
        if not self.tor_handler:
            self.tor_handler = TorHandler(self.config.tor_password(), self.config.tor_port(), self.config.http_proxy(), self.config.venv_path())
        self.actual_ip = self.tor_handler.get_ip()

        self.downloader = Downloader(5, torhandler=self.tor_handler, restart_tor=self.config.restart_tor(), waiting_time=self.wait_request)
        self.downloader.start()

        # Get the right scraper through the Creator class
        website = self.config.project_name().split("-")[0]
        product_category = self.config.project_name().split("-")[3]
        
        self.scraper = Creator.create_scraper(website, product_category)

        # Get the right captcha detector through the Creator class
        self.captcha_detector = Creator.create_captcha_detctor(website)

        self.cookie_handler = None
        if self.config.has_cookies(seed):
            self.cookie_handler = CookieHandler(self.seed, self.tor_handler, self.captcha_detector)

            self.bucket_cookies = None
            self.cookies = None
            self.cookie_wait = False

        if not self.scraper:
            raise ValueError("Expected a non-None value from create_scraper(), but got None")

        # Config info
        data_dir = self.config.data_dir()

        # - Project directory
        if project_path is None:
            today_tms = datetime.now().strftime("%Y%m%d")
            project_name = f"{self.config.project_name()}-{today_tms}"
            project_path = os.path.join(data_dir, project_name)

        if os.path.exists(project_path):
            error_msg = f"Error: The project folder '{project_path}' already exists."
            raise FileExistsError(error_msg)

        os.makedirs(project_path, exist_ok=True)

        # Pages folder
        self.page_path = os.path.join(project_path, "pages")
        os.makedirs(self.page_path)

        # Images folder
        self.image_path = os.path.join(project_path, "images")
        os.makedirs(self.image_path)

        # Mapping images - data crawled
        self.image_mapping_path = os.path.join(self.image_path, "image_mapping.csv")
        if not os.path.exists(self.image_mapping_path):
            with open(self.image_mapping_path, "w") as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(["website", "image", "web_page", "url", "depth_node", "index_node", "title", "description", "vendor", "origin", "destination", "currency", "price", "cryptocurrency", "crypto_price", "macro_category", "micro_category"])


        self.monitor = CrawlerMonitor(project_path)
        self.monitor.start_scheduling()

        self.filesaver = FileSaver(self.page_path)
        self.filesaver.start()

        # Get the macro and micro category
        split_project_name = self.config.project_name().split("-")
        flag = bool(input("Are the images url of the seed encoded in base64? (0=no, 1= yes)\n"))
        self.imagesaver = ImageSaver(f"{split_project_name[0]} {split_project_name[1]}", self.image_path, self.image_mapping_path, split_project_name[2], split_project_name[3], self.tor_handler, flag)
        self.imagesaver.start()
    
    def require_cookies(self):
        return self.config.requires_cookies(self.seed)

    def get_info(self):
        return self.monitor.get_info()

    def get_webpage_url(self, webpage):
        if not webpage:
            return None

        if len(webpage.history) > 0:
            return webpage.history[-1].url

        return webpage.url

    def extract_internal_buttons(self, web_page) -> list:
        """
        Extract the internal buttons of a web page
        :param web_page: the web page
        :return: list of links provided by the buttons in the web page
        """
        print("Internal buttons extraction...")
        logger.info(f"{self.seed} - Internal buttons extraction")
        
        website = self.config.project_name().split("-")[0]

        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")
        urls = set()

        # Get all internal buttons
        buttons = soup.findAll("button")
        logger.info(f"Number of internal buttons: {len(buttons)}")

        if website == "drughub":
            
            for button in buttons:
                # Get the value attribute of the button
                value = button.get("value")
                # Get the button text
                text_content = button.text.strip()

                # Check if the button value and text are a digit and they are not None
                if value and text_content and value.isnumeric() and (text_content.isnumeric() or text_content == "»"):
                    value = int(value)
                    if value != 0:
                        url = urljoin(self.seed, f"?page={value}")
                        urls.add(url)
        
        urls_list = list(urls)
        print(f"Number of extracted button links: {len(urls_list)}")
        logger.info(f"Number of extracted button links: {len(urls_list)}")
        
        return urls_list
    
    def extract_internal_links(self, web_page) -> list:
        """
        This function, using Beautifulsoup4, search for all the internal links (links of the same website)
        in a web page.
        :param web_page: the web_page content retrieved from a request (return value of request.get function).
        :return: a list of url found in the web_page
        """
        print("Internal link extraction...")
        logger.info(f"{self.seed} - Internal link extraction")

        request_url = web_page.request.url
        logger.debug(f"{self.seed} - Internal links - Request URL -> {request_url}")
        domain = urlparse(request_url).netloc

        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")

        urls = set()
        # Get the seed to filter the internal links -> RENDERE GENERALE
        x = urlparse(self.seed).path.split("/")
        url_category = "/".join(x[-2:])
        print(f"Category in url format: {url_category}")
          
        # Get all internal links
        tags = soup.findAll("a")
        print(f"Number of internal links {len(tags)}")
        logger.info(f"Number of internal links {len(tags)}")
        for a_tag in tags:
            href = a_tag.attrs.get("href")
            href = urljoin(request_url, href).strip("/")
            # logger.debug(f"{self.market.upper()} - Internal links - Extracting link {href}")

            if href == "" or href is None:
                # href empty tag
                continue

            if urlparse(href).netloc != domain:
                # external link
                continue
                
            if "vendor" in href:
                # The internal link is not a products link
                continue

            if "#" in href:
                # The internal link points to a section within the current web page
                continue

            if "login" in href:
                # The internal link points to a login page
                continue

            if url_category not in href:
                # The internal link points to a info page
                continue
            
            urls.add(href)

        urls_list = list(urls)
        
        print(f"Number of internal links extracted: {len(urls_list)}")
        logger.info(f"Number of internal links extracted: {len(urls_list)}")

        # Get the internal links provided by the buttons
        buttons_url = self.extract_internal_buttons(web_page)

        # Concatenate the two lists
        urls_list = urls_list + buttons_url
        
        return urls_list

    def extract_internal_images(self, web_page) -> list:
        """
        Extract all the images on the web page
        :param web_page: the web_page content retrieved from a request (return value of request.get function).
        :return: a list of images in the web page given as input
        """
        print("Extracting internal images...")
        logger.info(f"{self.seed} - Internal images extraction")
        images = list()

        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")

        # Get all images
        tags = soup.findAll("img")
        print(f"Number of img tags found in the web page is: {len(tags)}")
        logger.info(f"Number of img tags found in the web page is: {len(tags)}")
        
        for img_tag in tags:
            if img_tag.has_attr("class"):
                class_value = " ".join(img_tag["class"])

                # Check if the image is valid
                if self.scraper.check_image(class_value): 
                    print("The image has the class name that I want")
                    src_tag = None
                    try:
                        src_tag = img_tag["src"]
                    except KeyError:
                        print(f"Found <img> tag without 'src' attribute")
                        logger.warning(f"{self.seed} - Found <img> tag without 'src' attribute")
                        continue 

                    # Check the image extension
                    if "jpg" in src_tag or "jpeg" in src_tag or "png" in src_tag:
                        images.append(src_tag)
                    else:
                        logger.info(f"{self.seed} - The image {src_tag} hasn't the right extension")

        print(f"Number of images to download for this web page: {len(images)}")
        logger.info(f"Number of images to download for this web page: {len(images)}")
        return images

    def check_webpage_lang(self, web_page) -> bool:
        """
        Check if the web page language is in english
        :param web_page: tweb page content
        :return: True if the web page content is in english, false otherwise
        """
        print("Checking the web page language...")
        # Make soup
        soup = BeautifulSoup(web_page.content, "html.parser", from_encoding="iso-8859-1")
        html_tag = soup.find("html")

        if html_tag and html_tag.get("lang") == "en":
            print("The web page is written in english")
            return True
        else:
            return False


    def enqueue_url(self, url) -> None:
        # TOR request
        cookie = None

        if self.require_cookies():
            # Try to acquire a new cookie
            cookie = self.cookie_handler.get_random_cookie(url, validity_check=False)

            # No cookies in yml file. Wait new cookies
            if not cookie:
                cookie = wait(lambda: self.cookie_handler.get_random_cookie(url, validity_check=False),
                              sleep_seconds=1, timeout_seconds=MAX_COOKING_WAITING_TIME, waiting_for="waiting for new cookies.")

        self.downloader.enqueue(url, cookie)

    def validate(self, web_page) -> bool:
        """
        Check if the url content is valid, without captchas or without any anomalous redirection.
        If something is found, then the cookie used for that page is removed.
        :param web_page: the web page to validate
        :return: True, if the page contains no captchas or anomalous redirect, False otherwise.
        """

        if not self.config.has_cookies(self.seed):
            return True

        captcha = captcha_detector(web_page.url, web_page)
        login_redirect = True
        if self.login_page:
            login_redirection(web_page, self.login_page)

        if login_redirect or captcha:
            if captcha:
                logger.info(f"{self.seed} - Captcha FOUND in link {web_page.url}. Request new cookie.")
            else:
                logger.info(f"{self.seed} - Redirection to login page. Cookie expired. Request new cookie.")

            return True

        return False

    def start(self) -> None:
        """
        Method to execute the crawler.
        :return: no return value. All the web_pages will be saved in a dump folder.
        """
        # Track visited URLs to avoid duplicates
        visited = {}
        unvisited_links = set()
        try:
            if not self.seed:
                logger.error(f"No valid seed -> {self.seed}")
                raise InvalidURLException(f"No valid seed -> {self.seed}")

            print("Saving the login page...")
            if self.config.has_cookies(self.seed):
                # Assumption: all the markets with no valid cookies redirect to the same page with the same url
                logger.info(f"{self.seed} - Send a request without cookie to store the login redirect url")

                self.login_page = self.tor_handler.send_request(self.seed)
                self.cookie_handler.nocookiepage = self.login_page
                # logger.info(f"{self.market.upper()} - URL no cookie default redirect -> {self.loginpage.url}")

                # Get a valid cookie among the cookies stored in the market configuration file
                self.cookie_handler.cookies_validity_check(self.seed)

            # Create a queue for BFS
            self.enqueue_url(self.seed)
            node_index = 0

            # Crawling iter condition
            # 1. all the urls are crawled
            # 2. if the cookie expiration time has been reached
            # 3. the maximum allowed number of links, defined in the config.ini file, has been reached
            # 4. expiration time defined in the config.ini file
            cookie_timeout = False
            start_time = time.time()
            n_links_crawled = 0
            url_depth = {self.seed: 0}
            url_attempts = {}
            retry_counts = {}

            n_images = 0
            n_wrong_category = 0
            count = 0

            while (not self.downloader.is_empty() and n_links_crawled < self.max_link and not cookie_timeout and
                   time.time() - start_time < self.max_crawl_time):
                
                count += 1

                try:
                    #ottiene tutti i task completati, quindi le pagine del dark web
                    url_futures = self.downloader.get_results()
                    logger.debug(f"{self.seed} - CRAWLER: futures len -> {len(url_futures)}")

                    # If no pages are available, wait for the thread to complete.
                    if not url_futures:
                        time.sleep(0.1)
                        continue

                    self.monitor.update_tor_requests(self.tor_handler.n_requests_sent)

                    for url, future in url_futures:
                        logger.info(f"*********** Analyzing the url {url} ***********")
                        if url in visited:
                            print(f"*********** Analyzing the node {visited[url]} ***********")
                        else:
                            print(f"*********** Analyzing the node {node_index} ***********")
                        
                        try:
                            web_page = future.result() #get the web page
                            print(f"The url of the web page requested is: {web_page.url}")
                        except Exception as e:
                            print(f"ERROR with this url: {url}")
                            
                            # Retry to crawl the web page only if the number of attempts is less than the maximum
                            if url not in retry_counts:
                                print("Retry with this url later")
                                logger.debug(f"Error while downloading the url -> {url}. RETRY.")
                                retry_counts[url] = 1
                                self.enqueue_url(url)
                            elif retry_counts[url] < MAX_RETRIES:
                                retry_counts[url] += 1
                                print("Retry with this url later")
                                logger.debug(f"Error while downloading the url -> {url}. RETRY. Attempts: {retry_counts[url]}")
                                self.enqueue_url(url)
                            else:
                                print("Error while processing a webpage. SKIP.")
                                logger.error(f"{url} - Error while processing a webpage. SKIP.")
                                logger.error(f"{url} - Error msg: {str(e)}")
                                self.monitor.add_info_unvisited_page(int(time.time()), url, self.actual_ip, "ERROR")
                            continue

                        if not web_page:
                            continue

                        # Check if the page is valid or not.
                        if self.captcha_detector.has_captcha(web_page.content) or not self.validate(web_page):
                            print("The web page contains a captcha")

                            if url not in url_attempts:
                                url_attempts[url] = 1
                                self.enqueue_url(url)
                                logger.debug(f"{self.seed} - Error while downloading the url -> {url}. RETRY.")
                            elif url_attempts[url] < MAX_RETRIES:
                                url_attempts[url] += 1
                                self.enqueue_url(url)
                                logger.debug(f"{self.seed} - Error while downloading the url -> {url}. RETRY.")
                            else:
                                logger.error(f"{self.seed} - Error while downloading the url -> {url}. SKIPPED.")
                                self.monitor.add_info_unvisited_page(int(time.time()), url, self.actual_ip, "ERROR")
                            
                            continue

                        # STATUS CODE CHECK
                        if web_page.status_code < 200 or web_page.status_code >= 300:
                            self.monitor.add_info_page(int(time.time()), url, self.actual_ip, web_page.status_code)
                            continue
                        
                        # Check if the page is in english
                        if not self.check_webpage_lang(web_page):
                            print("The web page is not written in english")
                            logger.info(f"{self.seed} the web page is not written in english")
                            continue
                        
                        # Check if the current web page is in the right category
                        if not self.scraper.check_category(web_page):
                            print(f"The web page category is wrong. URL: {url}")
                            logger.info(f"The web page category is wrong. URL: {url}")
                            n_wrong_category += 1

                            # Save it to inspect afterwards
                            # self.filesaver.enqueue(web_page, visited[url])
                            continue

                        # Extract all the internal link in the web page
                        try:
                            internal_urls = self.extract_internal_links(web_page)
                            logger.debug(f"{self.seed} - Internal links: {len(internal_urls)}.")
                        except Exception as e:
                            logger.error(f"{self.seed} - Internal link extraction failed..")
                            logger.error(f"{self.seed} - Error msg: {str(e)}")
                            print("Internal link extraction failed...")
                            print(f"Error message: {str(e)}")
                            continue
                        
                        # Extract all the images in the web page
                        internal_images = None
                        if node_index != 0: # To jump the image in the seed
                            try:
                                internal_images = self.extract_internal_images(web_page)
                                n_images += len(internal_images)
                            except Exception as e:
                                logger.error(f"{self.seed} - Internal images extraction failed..")
                                logger.error(f"{self.seed} - Error msg: {str(e)}")
                                print("Internal images extraction failed...")
                                print(f"Error message: {str(e)}")
                                continue

                        # Get product information only if the crawler captures at least one image to download.
                        product_information = None
                        if internal_images and len(internal_images)>0:
                            product_information = self.scraper.extract_product_information(web_page)

                        try:
                            logger.debug(f"{self.seed} - URL: {url}.")
                            depth = url_depth[url]
                            logger.debug(f"{self.seed} - DEPTH: {depth}.")
                            del url_depth[url]
                        except Exception as e:
                            logger.error(f"{self.seed} - URL DEPTH.")
                            logger.error(f"{self.seed} - Error msg: {str(e)}")
                            raise e

                        # Add the url in the visited list
                        if url not in visited:
                            print("Add web page in the visited list")
                            visited[url] = node_index
                            self.monitor.add_node(url, node_index, depth, str(node_index)+".html")
                            node_index += 1

                        self.monitor.add_info_page(int(time.time()), url, self.actual_ip, web_page.status_code)

                        # Save the node_index of the actual url
                        actual_url_node_index = visited[url]

                        # Enqueue new links and add edges
                        if internal_urls and len(internal_urls)>0:
                        
                            print("Saving the internal links in the downloader queue...")
                            for link in internal_urls:
                                # Skip the link if the deep level is at least equal to the max deep level (configuration
                                # setting)
                                if depth + 1 > self.max_depth:
                                    logger.info(f"{self.seed} - URL {link}: depth value greater than {self.max_depth}. IGNORED.")
                                    unvisited_links.add(link)
                                    self.monitor.add_info_unvisited_page(int(time.time()), link, self.actual_ip, "MAX DEPTH")
                                else:
                                    if link not in visited and link not in unvisited_links:
                                        url_depth[link] = depth + 1

                                        # Save scheduled page
                                        self.monitor.add_scheduled_page(int(time.time()), link, self.actual_ip, depth + 1)

                                        self.enqueue_url(link)
                                        visited[link] = node_index #per non riprendere il link
                                        self.monitor.add_node(link, node_index, depth + 1, str(node_index)+".html")
                                        node_index += 1

                                    self.monitor.add_edge(visited[url], visited[link])

                        # Get cookie to make a Tor request to download the image
                        cookie = None
                        if self.require_cookies():
                            # Try to acquire a new cookie
                            cookie = self.cookie_handler.get_random_cookie(url, validity_check=False)

                        # No cookies in yml file. Wait new cookies
                        if not cookie:
                            cookie = wait(lambda: self.cookie_handler.get_random_cookie(url, validity_check=False),
                                        sleep_seconds=1, timeout_seconds=MAX_COOKING_WAITING_TIME, waiting_for="waiting for new cookies.")
                        
                        # Save the images
                        if actual_url_node_index != 0:
                            print("Saving the internal images in the ImageSaver queue...")
                            i = 0
                            for img in internal_images:
                                self.imagesaver.enqueue(img, url, actual_url_node_index, depth, cookie, i, product_information)
                                i += 1
                            

                        # Save the html page
                        print("Saving the html script in the FileSaver queue...\n")
                        self.filesaver.enqueue(web_page, visited[url])

                        n_links_crawled += 1
                        print("************************\n")
                        logger.info("************************\n")
                except TimeoutExpired as te:
                    logger.error(f"{self.seed} - Cookie timeout expired.")
                    logger.error(f"{self.seed} - Error msg: {str(te)}")
                    cookie_timeout = True
                
                if count % self.check_cookie == 0:
                    self.cookie_handler.cookies_validity_check(self.seed)
                    count = 0

            logger.info(f"Number of images downloaded: {n_images}")
            logger.info(f"Number of web pages with wrong category: {n_wrong_category}")

            if self.downloader.is_empty():
                logger.info(f"{self.seed} - Crawler END - All links have been crawled.")
            elif len(visited) >= self.max_link:
                logger.info(f"{self.seed} - Crawler END - The max_link set in the config.ini has been reached.")
            elif cookie_timeout:
                logger.info(f"{self.seed} - Crawler END - Cookie expiration time.")
            else:
                logger.info(f"{self.seed} - Crawler END - The max_crawl_time set in the config.ini has been reached.")
        except Exception as e:
            logger.error(f"{self.seed} - {str(e)}.")
            print(e)

        self.downloader.stop()
        self.monitor.stop_program()

        # Waiting that the image saver queue is empty
        while not self.imagesaver.is_empty():
            pass

        self.imagesaver.stop()

        # Waiting that the file saver queue is empty
        while not self.filesaver.is_empty():
            pass
        
        self.filesaver.stop()