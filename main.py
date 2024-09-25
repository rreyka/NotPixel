import requests
import json
import time
import random
from setproctitle import setproctitle
from convert import get
from colorama import Fore, Style, init
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib.parse

url = "https://notpx.app/api/v1"
WAIT = 180 * 3
DELAY = 1
WIDTH = 1000
HEIGHT = 1000
MAX_HEIGHT = 50

init(autoreset=True)
setproctitle("notpixel")
image = get("")
c = {
    '#': "#000000",
    '.': "#3690EA",
    '*': "#ffffff"
}

def log_message(message, color=Style.RESET_ALL):
    current_time = datetime.now().strftime("[%H:%M:%S]")
    print(f"{Fore.LIGHTBLACK_EX}{current_time}{Style.RESET_ALL} {color}{message}{Style.RESET_ALL}")

def get_session_with_retries(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = get_session_with_retries()

def get_color(pixel, header):
    try:
        response = session.get(f"{url}/image/get/{str(pixel)}", headers=header, timeout=10)
        if response.status_code == 401:
            return -1
        return response.json()['pixel']['color']
    except KeyError:
        return "#000000"
    except requests.exceptions.Timeout:
        log_message("Request timed out", Fore.RED)
        return "#000000"
    except requests.exceptions.ConnectionError as e:
        log_message(f"Connection error: {e}", Fore.RED)
        return "#000000"
    except requests.exceptions.RequestException as e:
        log_message(f"Request failed: {e}", Fore.RED)
        return "#000000"

def claim(header):
    log_message("Claiming resources", Fore.CYAN)
    try:
        session.get(f"{url}/mining/claim", headers=header, timeout=10)
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to claim resources: {e}", Fore.RED)

def get_pixel(x, y):
    return y * len(image[0]) + x + 1

def get_pos(pixel, size_x):
    return pixel % size_x, pixel // size_x

def get_canvas_pos(x, y):
    return get_pixel(start_x + x - 1, start_y + y - 1)

start_x = 920
start_y = 386

def paint(canvas_pos, color, header):
    data = {"pixelId": canvas_pos, "newColor": color}
    try:
        response = session.post(f"{url}/repaint/start", data=json.dumps(data), headers=header, timeout=10)
        x, y = get_pos(canvas_pos, 1000)
        if response.status_code == 400:
            log_message("Out of energy", Fore.RED)
            return False
        if response.status_code == 401:
            return -1
        log_message(f"Paint: {x},{y}", Fore.GREEN)
        return True
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to paint: {e}", Fore.RED)
        return False

def extract_username_from_initdata(init_data):
    decoded_data = urllib.parse.unquote(init_data)
    username_start = decoded_data.find('"username":"') + len('"username":"')
    username_end = decoded_data.find('"', username_start)
    if username_start != -1 and username_end != -1:
        return decoded_data[username_start:username_end]
    return "Unknown"

def load_accounts_from_file(filename):
    with open(filename, 'r') as file:
        accounts = [f"initData {line.strip()}" for line in file if line.strip()]
    return accounts

def fetch_mining_data(header):
    try:
        response = session.get(f"https://notpx.app/api/v1/mining/status", headers=header, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_balance = data.get('userBalance', 'Unknown')
            log_message(f"Balance: {user_balance}", Fore.MAGENTA)
        else:
            log_message(f"Failed to fetch mining data: {response.status_code}", Fore.RED)
    except requests.exceptions.RequestException as e:
        log_message(f"Error fetching mining data: {e}", Fore.RED)

def main(auth, account):
    headers = {'authorization': auth}
    try:
        fetch_mining_data(headers)
        claim(headers)
        size_y = len(image)
        size_x = len(image[0])

        while True:
            x = random.randint(0, size_x - 1)
            y = random.randint(0, size_y - 1)
            time.sleep(0.05 + random.uniform(0.01, 0.1))
            try:
                color = get_color(get_canvas_pos(x, y), headers)
                if color == -1:
                    log_message("DEAD :(", Fore.RED)
                    print(headers["authorization"])
                    break
                if image[y][x] == ' ' or color == c[image[y][x]]:
                    log_message(f"Skip: {start_x + x - 1},{start_y + y - 1}", Fore.RED)
                    continue
                result = paint(get_canvas_pos(x, y), c[image[y][x]], headers)
                if result == -1:
                    log_message("DEAD :(", Fore.RED)
                    print(headers["authorization"])
                    break
                elif result:
                    continue
                else:
                    break
            except IndexError:
                log_message(f"IndexError at x: {x}, y: {y}", Fore.RED)
    except requests.exceptions.RequestException as e:
        log_message(f"Network error in account {account}: {e}", Fore.RED)

def process_accounts(accounts):
    first_account_start_time = datetime.now()
    for account in accounts:
        username = extract_username_from_initdata(account)
        log_message(f"--- STARTING SESSION FOR ACCOUNT: {username} ---", Fore.BLUE)
        main(account, account)
    time_elapsed = datetime.now() - first_account_start_time
    time_to_wait = timedelta(hours=1) - time_elapsed
    if time_to_wait.total_seconds() > 0:
        log_message(f"SLEEPING FOR {int(time_to_wait.total_seconds() // 60)} MINUTES", Fore.YELLOW)
        time.sleep(time_to_wait.total_seconds())
    else:
        log_message(f"NO SLEEP NEEDED, TOTAL PROCESSING TIME EXCEEDED 1 HOUR", Fore.YELLOW)

if __name__ == "__main__":
    accounts = load_accounts_from_file('data.txt')
    while True:
        process_accounts(accounts)
