import re
import socket

# Local import
from handler import TorCookiesHandler
from utils.config import Configuration
from utils.seeds import get_seeds

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

if __name__ == '__main__':
    config = Configuration()

    # Get the seed to be crawled
    seeds = get_seeds()
    seed = None
    if len(seeds) == 1:
        seed = seeds[0]

    # Define a regulare expression to extract all the onion url
    pattern = rf"(.*?{re.escape('.onion/')})"
    match = re.search(pattern, seed)
    homepage_url = None
    if match:
        homepage_url = match.group(1)
    
    tor_cookie_handler = TorCookiesHandler(config.tor_password(), config.second_tor_port(), config.second_tor_proxy(), config.venv_path(), config.cookie_waiting_time(), config.cookie_attempts(), homepage_url, seed)
    
    # Get the Tor port used by the crawler
    crawler_tor_port =config.tor_port()
    n_cookies = 0

    # Store cookies until the crawler doesn't stop
    while is_port_open("127.0.0.1", crawler_tor_port):
        tor_cookie_handler.store_new_cookie()
        print("*************************\n")
        n_cookies += 1
    
    print(f"Number of cookie extracted: {n_cookies}")
    tor_cookie_handler.stop_tor_process()