# CRATOR
![OncoVision logo](./tarantula.png)

The project goal is to develop a web crawler tailored for extracting data from drug marketplaces on the dark web. The extracted data will be used to build a dataset for training an AI model capable of classifying different types of drugs. The crawler is designed to collect web pages and drug information (title, description, vendor name, shipping information, price, cryptocurrency price, macro-category, and micro-category) from various marketplaces.

## ⚙️ ​Project structure

 * **python** folder contains all the necessary scripts;
    * **detectors** folder contains custom scripts for each dark web marketplace to detect the captchas and waiting pages;
    * **scrapers** folder contains custom scripts for each dark web marketplace to scrape them;
    * **utils** folder contains scripts to handle the crawler configuration and utility function to store data;
 * **resources** folder contains the seed from which the crawler starts and a YAML file to configure it;

## 💻 Project environment setup

 To run the crawler, please ensure you have the required dependencies installed. You can do this by executing the following command in your terminal:
 
 ```bash
 pip install -r requirements.txt
 ```

 Then, you should have installed Tor on your machine. If you don't have it yet, you can run this command in the Linux terminal:

 ```bash
 sudo apt install tor
 ```

 Create a new Tor configuration file, namely a new torrc file and define these three fields:
 * SocksPort
 * DataDirectory
 * ControlPort
 * HashedControlPassword

 You can generate your hashed Tor password with this command:
 
 ```bash
 tor --hash-password "your_password"
 ```

## 🧑🏻‍💻 Usage

 To run the crawler, you should setup the YAML file and the `seed.txt` in the resources folder. Follow these steps to configure the YAML file:
 * Define a path in the `data_directory` field where the crawled data will be stored.
 * Define the `project_name` field.
 * Define in the `http_proxy` the HTTP proxy address to route traffic through Tor. This should be in the format 'socks5h://127.0.0.1:PORT', where PORT corresponds to the SOCKS port on which the **first** Tor instance is listening.
 * Define in the `second_tor_proxy` the HTTP proxy address to route traffic through Tor. This should be in the format 'socks5h://127.0.0.1:PORT', where PORT corresponds to the SOCKS port on which the **second** Tor instance is listening.
 * Define in the `tor_port` field the port number on which the Tor control port is listening (of the **first** Tor instance).
 * Define in the `second_tor_port` field the port number on which the Tor control port is listening (of the **second** Tor instance).
 * Define in the `tor_password` field the password required to authenticate with the Tor control port. It should match the hashed password set in the Tor configuration file (torrc).
 * Define in the `restart_tor` field the number of HTTP requests after which restart the **first** Tor instance.
 * Define in the `crawler.depth` field the maximum depth at which the crawler can reach.
 * Define in the `crawler.wait_request` field the waiting time between two HTTP requests (in milliseconds).
 * Define in the `venv_path` field the path of your python virtual environment. You can obtain it in this way: activate the environment and then execute this command `which python`.
 * Define in the `check_cookie` field the number after which check the cookies' validity stored in the YAML file.
 * Define in the `cookie_attempts` field the maximum number of attempts to try to acquire a new cookie with `extract_cookie.py`.
 * Define in the `cookie_waiting_time` field the amount of waiting time between two HTTP requests in case the acquiring cookie procedure encounters an issue.
 * Write in the `crawler.cookies.seed` field the seed link to be crawled.
 * Add two or more HTTP request cookie values in the `crawler.cookies` field for the corresponding seed, so the crawler can start.

 You can see the actual YAML file to understand how setup it.

 Then write the seed link in the seed.txt. It should be the same link that you provide in the YAML file.

 After which you should start the two Tor instances. You can run the first one with this command:
 
 ```bash
 sudo systemctl start tor
 ```

 instead, you can run the second Tor instance with this other command:

 ```bash
 tor -f path_to_torrc_file
 ```

 To check if the two Tor instances are running you can execute this command:

 ```bash 
 ss -nlt
 ```

 Then open a new terminal in your IDE and split it. In the first window run the crator.py file to crawl the dark web marketplace, instead in the second window run the extract_cookie.py file to acquire a new cookie to store in the YAML file.

## Future works

## 📧 ​Contact

 Rocco Iuliano - rocco.iul2000@gmail.com