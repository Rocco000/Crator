import logging
import os
from datetime import datetime
import concurrent.futures

import crawler
from handler import TorHandler
from utils.config import Configuration
from utils.seeds import get_seeds

MAX_ITERATION = 10
DEPTHS = [1, 2, 3, 4]
CONFIG_FILES = ["/home/jadelab/git/Dark-Web-Crawler/resources/crator_1.yml",
                "/home/jadelab/git/Dark-Web-Crawler/resources/crator_2.yml",
                "/home/jadelab/git/Dark-Web-Crawler/resources/crator_3.yml",
                "/home/jadelab/git/Dark-Web-Crawler/resources/crator_4.yml"]
EXP_PATH = "/home/jadelab/git/Dark-Web-Crawler/experimentation/"


def init_logger():
    log_directory = "../log/experimentation"
    if not os.path.exists(log_directory) or not os.path.isdir(log_directory):
        os.mkdir(log_directory)

    today_tms = datetime.now().strftime("%Y%m%dT%H%M%S")
    logfile_path = os.path.join(log_directory, f"crator_{today_tms}.log")

    # Create a logger object
    logger = logging.getLogger("CRATOR")
    logger.setLevel(logging.DEBUG)

    # Create a file handler to write logs to a file
    file_handler = logging.FileHandler(logfile_path)
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter to format the logs
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)


if __name__ == '__main__':
    print("CRATOR Experimentation.")

    for config_path in CONFIG_FILES:
        config = Configuration(config_path)
        depth = config.depth()
        data_dir = config.data_dir()

        print(f"Analyzing level of depth {depth}...")

        for i in range(MAX_ITERATION):
            print(f"Experimentation {i+1}")

            today_tms = datetime.now().strftime("%Y%m%d")
            exp_folder_name = f"{today_tms}-depth-{depth}-exp{i+1}"
            experimentation_folder = os.path.join(data_dir, exp_folder_name)

            init_logger()
            logger = logging.getLogger("CRATOR")
            logger.info("CRATOR - START")

            seeds = get_seeds()
            logger.info(f"Urls to analyze: {', '.join(seeds)}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(seeds)) as executor:
                torhandler = TorHandler()
                crators = []
                futures = []

                print(f"Seeds: {len(seeds)}")
                for seed in seeds:
                    print(f"Seed {seed} added to the thread pool")
                    crator = crawler.Crawler(seed, tor_handler=torhandler, crator_config_path=config_path,
                                             project_path=experimentation_folder)
                    crators.append(crator)

                    future = executor.submit(crator.start)
                    futures.append(future)

                print("Threads: START.")

                # Wait for all tasks to complete
                concurrent.futures.wait(futures)

                print("Threads: END.")

                logger.info("CRATOR - END")
