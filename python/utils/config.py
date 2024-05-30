import yaml
import os
from pathlib import Path

resource_path = Path(__file__).parent.parent.parent.joinpath("resources")


class Configuration:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Configuration, cls).__new__(cls)
        return cls._instance

    def __init__(self, yml_path=None):
        self.crator_path = yml_path
        if not self.crator_path:
            self.crator_path = os.path.join(resource_path, 'crator.yml')

        if not os.path.isfile(self.crator_path):
            raise FileNotFoundError(f"Invalid path: '{self.crator_path}' does not exist.")

        self.last_checked_time = None
        self.load_yaml()

    def is_updated(self):
        # Get the modification timestamp of the file
        file_modified_time = os.path.getmtime(self.crator_path)

        if not self.last_checked_time:
            self.last_checked_time = file_modified_time
            return True

        # Compare the file's modification time with the last checked time
        if file_modified_time > self.last_checked_time:
            print("file yaml modificato!")
            self.last_checked_time = file_modified_time
            return True
        else:
            return False

    def load_yaml(self):
        if self.is_updated():
            print("carico i dati del file yaml")
            with open(self.crator_path, 'r') as file:
                self.config = yaml.safe_load(file)

    def project_name(self):
        if 'project_name' in self.config:
            return self.config['project_name']

        return 'default'

    def http_proxy(self):
        return self.config['http_proxy']
    
    def second_tor_proxy(self):
        return self.config["second_tor_proxy"]

    def max_links(self):
        return self.config['crawler.max_links']

    def max_time(self):
        return self.config['crawler.max_time']

    def wait_request(self):
        return self.config['crawler.wait_request']

    def depth(self):
        return self.config['crawler.depth']

    def data_dir(self):
        return self.config['data_directory']
    
    def tor_port(self):
        return self.config['tor_port']
    
    def second_tor_port(self):
        return self.config['second_tor_port']

    def restart_tor(self):
        return self.config["restart_tor"]
    
    def tor_password(self):
        return self.config["tor_password"]
    
    def cookie_waiting_time(self):
        return self.config["cookie_waiting_time"]
    
    def cookie_attempts(self):
        return self.config["cookie_attempts"]
    
    def venv_path(self):
        return self.config["venv_path"]

    def requires_cookies(self, seed):
        """
        Check if the yaml file there are cookies for the seed web site
        """
        self.load_yaml()

        if 'crawler.cookies' not in self.config:
            return False

        if not seed:
            return False

        for cookie_by_seed in self.config.get('crawler.cookies', []):
            if cookie_by_seed.get('seed') == seed:
                return True

        return False

    def has_cookies(self, seed):
        self.load_yaml()

        if 'crawler.cookies' not in self.config:
            print("non c'e' il campo crawler.cookies nel yaml file")
            return False

        if not seed:
            print("seed non fornito")
            return False
        #     return 'crawler.cookies' in self.config

        for cookie_by_seed in self.config.get('crawler.cookies', []):
            # Cosa fa il 2 controllo?
            # print("controllo non compreso in has_cookies:")
            if cookie_by_seed.get('seed') == seed and 'cookies' in cookie_by_seed:
                print("trovato cookie per il seed")
                return True

        print("non c'e' un cookie per il seed")
        return False

    def cookies(self, seed):
        print("\nfunzione cookies")
        #self.load_yaml() gia' c'era questa riga
        #print("Valore di has_cookies: ")
        #print(self.has_cookies())
   
        flag_has_cookie = False
        self.load_yaml()

        if 'crawler.cookies' not in self.config:
            print("non c'e' il campo crawler.cookies nel yaml file")
            flag_has_cookie = False

        if not seed:
            print("seed non fornito")
            flag_has_cookie = False

        for cookie_by_seed in self.config.get('crawler.cookies', []):
            if cookie_by_seed.get('seed') == seed and 'cookies' in cookie_by_seed:
                flag_has_cookie = True
                break

        if not seed or not flag_has_cookie:#self.has_cookies():
            print("return None 1")
            return None

        for cookie_by_seed in self.config.get('crawler.cookies', []):
            if cookie_by_seed.get('seed') == seed and 'cookies' in cookie_by_seed:
                return cookie_by_seed.get('cookies')

        return None

    def remove_cookie(self, seed, cookie):
        self.load_yaml()

        cookies = self.config.get('crawler.cookies', [])

        # Find the selected seed in the cookies list
        for i, seed_data in enumerate(cookies):
            if seed_data.get('seed') == seed and 'cookies' in seed_data and isinstance(seed_data['cookies'], list):
                seed_cookies = seed_data['cookies']

                # Remove the specified cookie from the seed's cookies
                if cookie in seed_cookies:
                    seed_cookies.remove(cookie)

        # Update the modified cookies list in the configuration
        self.config['crawler.cookies'] = cookies

        # Dump modified data back to YAML
        with open(self.crator_path, 'w') as file:
            yaml.dump(self.config, file)

    def add_cookie(self, seed, cookie):
        self.load_yaml()

        if 'crawler.cookies' not in self.config:
            self.config['crawler.cookies'] = []

        cookies = self.config.get('crawler.cookies', [])

        # Find the selected seed in the cookies list
        i = 0
        fetched = False
        while i < len(cookies) and not fetched:
            if cookies[i].get('seed') == seed and 'cookies' in cookies[i] and isinstance(cookies[i]['cookies'], list):
                cookies[i]['cookies'].append(cookie)
                fetched = True
            i += 1

        if not fetched:
            cookies.append({'seed': seed, 'cookies': [cookie]})

        # for i, seed_data in enumerate(cookies):
        #     if seed_data.get('seed') == seed and 'cookies' in seed_data and isinstance(seed_data['cookies'], list):
        #         seed_data['cookies'].append(cookie)
        #         break

        # Update the modified cookies list in the configuration
        self.config['crawler.cookies'] = cookies

        # Dump modified data back to YAML
        with open(self.crator_path, 'w') as file:
            yaml.dump(self.config, file)

    def remove_seed(self, seed):
        self.load_yaml()

        cookies = self.config.get('crawler.cookies', [])

        # Remove the seed and update the modified cookies list in the configuration
        self.config['crawler.cookies'] = [cookie for cookie in cookies if cookie.get('seed') != seed]

        if not self.config['crawler.cookies']:
            del self.config['crawler.cookies']

        # Dump modified data back to YAML
        with open(self.crator_path, 'w') as file:
            yaml.dump(self.config, file)
