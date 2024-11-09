from base_cookie_extractor import BaseCookieExtractor
import time
import requests

class CocoricoCookieExtractor(BaseCookieExtractor):
    """
    Extracts cookies for the Cocorico website using the Tor network.

    This class handles the specific logic required to obtain cookies from the Cocorico website.
    It inherits from the BaseCookieExtractor and uses a TorHandler instance for HTTP requests.
    """
    def get_new_cookie(self) -> str:
        attempt = 0
        cookie_value = None

        while cookie_value is None and attempt < self.attempts:
            try:
                # Make an HTTP request
                response = self.tor_handler.send_request(self.homepage_url)

                print(f"CocoricoCookieExtractor - STATUS CODE first HTTP request:{response.status_code}")
                
                cookie_value = f"OCSESSID={response.cookies.get('OCSESSID')}; language=en-gb; currency=EUR"

                time.sleep(self.waiting_time)
            except requests.RequestException as e:
                print(f"CocoricoCookieExtractor - Connection error occurred:\n{e}.\nRetrying in 1 minute...")
                time.sleep(60)
            
            attempt += 1

        return cookie_value