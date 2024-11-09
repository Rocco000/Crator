import re
import socket
import time

# Local import
from creator import Creator
from utils.config import Configuration
from utils.seeds import get_seeds
from handler import TorHandler

def is_port_open(host, port):
    """
    Check if a specific port is open on the given host.

    :param host: The host to check (usually '127.0.0.1' for localhost).
    :param port: The port to check.
    :return: True if the port is open, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)  # Set a timeout for the connection attempt
        result = sock.connect_ex((host, port))
        return result == 0
    
def delay_based_on_cookie_extracted(seed: str, config: Configuration) -> None:
    """
    Delay the cookie extraction based on number of cookies stored in the YAML file.

    :param seed: the URL to be crawled
    :param config: a Configuration object which handles the YAML file
    """
    num_cookie_stored = len(config.cookies(seed))

    delay = 0

    if num_cookie_stored >= 50:
        delay = (2 * 60) + 30
    elif num_cookie_stored >= 40:
        delay =  2 * 60 
    elif num_cookie_stored >= 30:
        delay =  90  
    elif num_cookie_stored >= 20:
        delay = 60
    elif num_cookie_stored >= 10:
        delay = 30
    else:
        delay = 0

    print(f"Reached {num_cookie_stored} cookies, delaying for {delay / 60} minute(s)...")
    time.sleep(delay)

if __name__ == '__main__':
    config = Configuration()

    # Get the seed to be crawled
    seeds = get_seeds()
    seed = None
    if len(seeds) == 1:
        seed = seeds[0]
    else:
        raise Exception("Define only one seed URL")

    scraper = Creator.create_scraper(config.marketplace(), config.macro_category(), config.micro_category())

    # Get the homepage URL
    homepage_url = scraper.get_base_url(seed)
    print(f"Homepage URL: {homepage_url}")

    tor_handler = TorHandler(config.tor_password(), config.second_tor_port(), config.second_tor_proxy(), config.venv_path())

    # Get the correct instance of cookie extractor
    cookie_extractor = Creator.create_cookie_extractor(tor_handler, homepage_url, seed, config.cookie_waiting_time(), config.cookie_attempts())
    
    # Get the Tor port used by the crawler
    crawler_tor_port = config.tor_port()
    n_cookies = 0
    counter = 1

    # Store cookies until the crawler doesn't stop
    while is_port_open("127.0.0.1", crawler_tor_port):
        print(f"Attempt {counter} to acquire a new cookie\n")
        result = cookie_extractor.store_new_cookie()

        counter += 1
        
        if result:
            print("*************************\n")
            n_cookies += 1
            counter = 1

        delay_based_on_cookie_extracted(seed, config)
        
    
    print(f"Number of cookie extracted: {n_cookies}")
    cookie_extractor.stop()