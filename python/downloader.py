import concurrent.futures
import os
import logging
import time
import threading
import random
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from handler import TorHandler


logger = logging.getLogger("CRATOR")


class Downloader:
    def __init__(self, n_threads, torhandler, restart_tor:int, waiting_time=1.5):
        """
        :param n_threads: number of threads to use
        :param torhandler: an istance of TorHandler
        :param restart_tor: number of HTTP requests after which Tor is restarted
        :param waiting_time: the amount of time in seconds that elapses between two HTTP requests
        """
        self.queue = deque()
        self.n_threads = n_threads
        self.waiting_time = waiting_time
        # number of HTTP requests after which Tor is restarted
        self.restart_tor = restart_tor

        if torhandler and not isinstance(torhandler, TorHandler):
            raise TypeError("Invalid type for torhandler parameter. It must be a TorHandler class.")

        self.torhandler = torhandler
        self.running = True
        self.lock = threading.Lock()
        self.results = []
        self.futures = [] #list of asynchronous task to run a function (tor_handler, right?)

        self.future_url_map = {}

        # To generate a random waiting time
        self.lower_bound = self.waiting_time-0.5 if self.waiting_time > 0 and self.waiting_time-0.5 > 0 else 0
        self.upper_bound = self.waiting_time+0.5 if self.waiting_time > 0 else 1.5

    def is_empty(self):
        # logger.debug(f"DOWNLOADER: Empty -> {not self.queue and not self.results}")
        return not self.queue and not self.futures

    def enqueue(self, url, cookie):
        """
        Add a tuple (url,coockie) to the queue
        """
        self.queue.append((url, cookie))

    def has_results(self):
        if self.get_results():
            return True

        return False

    def get_future_url(self, future):
        if id(future) not in self.future_url_map:
            return None

        return self.future_url_map[id(future)]

    def get_results(self):
        # logger.debug(f"DOWNLOADER: Results: queue before -> {len(self.queue)}")
        """
        Update the futures list in order to contain only the futures not completed
        :return: an iterator to wait and handle the completed tasks of a function
        """
        #create an iterator to wait and handle the completed tasks
        completed_futures = [future for future in concurrent.futures.as_completed(self.futures)]

        # Update self.futures to remove completed futures
        self.futures = [future for future in self.futures if future not in completed_futures]

        completed_futures = [(self.future_url_map.pop(id(future)), future) for future in completed_futures]

        return completed_futures

        # return [future.result() for future in completed_futures]
        #
        #
        # future_completed = []
        # for future in concurrent.futures.as_completed(self.futures):
        #     future_completed.append(future)
        #
        # for future in future_completed:
        #     self.futures.remove(future)
        #
        # return [future.result() for future in future_completed]

    def start(self):
        threading.Thread(target=self.download, daemon=True).start()

    def download(self):
        with ThreadPoolExecutor(max_workers=self.n_threads) as executor:
            while self.running:
                if not self.queue:
                    time.sleep(0.1)
                    continue

                with self.lock:
                    while self.queue:
                        url, cookie = self.queue.popleft()

                        future = executor.submit(self.torhandler.send_request, url, cookie)
                        self.futures.append(future)
                        self.future_url_map[id(future)] = url

                        if self.torhandler.n_requests_sent % self.restart_tor == 0:
                            print("DOWNLOADER - Restart Tor (crawling)!")
                            self.torhandler.renew_connection()
                        
                        # Get random waiting time
                        random_waiting_time = round(random.uniform(self.lower_bound, self.upper_bound), 2)
                        time.sleep(random_waiting_time)

    def stop(self):
        self.running = False

        # Stop Tor process
        self.torhandler.stop_tor_process()