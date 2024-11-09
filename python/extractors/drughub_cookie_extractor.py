from base_cookie_extractor import BaseCookieExtractor
import time
import requests

class DrughubCookieExtractor(BaseCookieExtractor):
    """
    Extracts cookies for the Drughub website using the Tor network.

    This class handles the specific logic required to obtain cookies from the Drughub website.
    It inherits from the BaseCookieExtractor and uses a TorHandler instance for HTTP requests.
    """

    def get_session_cookie_with_retries(self, cookies:requests.cookies.RequestsCookieJar) -> str:
        """
        This function tries to get the session cookie from the HTTP response
        :param  cookies: the cookies obtained from the first HTTP request
        :return: a string containing the session cookie, otherwise None if the website doesn't reply
        """
        for attempt in range(self.attempts):
            try:
                # Make the second HTTP request
                response_reload = self.tor_handler.send_request(self.homepage_url, cookies)
                status_code = response_reload.status_code

                print(f"DrughubCookieExtractor - STATUS CODE second HTTP request: {status_code}")

                # Get cookies
                reload_cookies = response_reload.cookies

                session = reload_cookies.get('session')

                if session:
                    return session
            except requests.RequestException as e:
                print(f"DrughubCookieExtractor - Connection error occurred during the second HTTP request:\n{e}.\nRetrying in 1 minute...")
                time.sleep(60)

            # Retries after self.waiting_time to make another HTTP request if the session is None            
            print(f"Attempt {attempt + 1} failed. Retrying in {self.waiting_time} seconds...")
            time.sleep(self.waiting_time)
        
        return None
    
    def get_new_cookie(self) -> str:
        primary = secondary = session = initial_cookies = None
        attempt = 0

        while not primary and not secondary and attempt < self.attempts:
            try:
                # Make first HTTP request
                first_response = self.tor_handler.send_request(self.homepage_url)
                status_code = first_response.status_code

                print(f"DrughubCookieExtractor - STATUS CODE first HTTP request:{status_code}")

                # Get cookies
                initial_cookies = first_response.cookies

                primary = initial_cookies.get("primary")
                secondary = initial_cookies.get("secondary")
                session = initial_cookies.get("session")

                # If all these cookies are None retry the first HTTP request
                if not primary and not secondary and not session:
                    print("All cookies are None. Retry with the first HTTP request")
                
                time.sleep(self.waiting_time)
            except requests.RequestException as e:
                print(f"DrughubCookieExtractor - Connection error occurred:\n{e}.\nRetrying in 1 minute...")
                time.sleep(60)
            
            attempt += 1

        if primary and secondary and not session:
            # Get session from the second HTTP request
            print("Trying to acquire the session cookie with a second HTTP request")
            session = self.get_session_cookie_with_retries(initial_cookies)

        if session:
            # Increase the counter of HTTP requests sent
            primary = primary.strip()
            secondary = secondary.strip()
            session = session.strip()
            
            return f"primary={primary}; secondary={secondary}; session={session}"
        else:
            return None