import time
import pickle
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
# Uses Xvfb to simulate a display


# Global Variables
DISCORD_USERNAME = "khi.thekhardist@gmail.com" # Discord Account Email
DISCORD_PASSWORD = "Ilovemymoms1!" # Discord Account Password

MANUAL_COOKIES = [
    {"name": "shopmagic_visitor_d5e9c3fbb247663e3be68a5c662d7379", "value": "%7B%22meta%22%3A%5B%5D%2C%22user_id%22%3A6424%7D"},
    {"name": "wordpress_logged_in_d5e9c3fbb247663e3be68a5c662d7379", "value": "liiiiia%7C1743962616%7CpwKHfLsoNEuZJPUNx5dQTVYR4ZQJog2xUbuPrvd9vGz%7C62f4a5a8d7a87565ff2ea1d7eafaf112c0548adc07f62bbb9afee725ca9c0733"},
    {"name": "wordpress_sec_d5e9c3fbb247663e3be68a5c662d7379", "value": "liiiiia%7C1743962616%7CpwKHfLsoNEuZJPUNx5dQTVYR4ZQJog2xUbuPrvd9vGz%7C5929c14b7d732632612011808ad07f18a49254bcb28db497ae533af4a354193e"}
]

COOLDOWN_DURATION_SECONDS = 3600

# Site Configuration
BASE_URL = 'https://pgbmemberpass.com/'
LOGIN_URL = 'https://pgbmemberpass.com/my-account/'
SHOP_URL = 'https://pgbmemberpass.com/shop/'

# Discord Webhook
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1349522889723871304/vnkTOfUS6ea34tubLzE6Tsu6Ar0GzEwHYcUFjNFybcFlF-eg6lpfDr60JRFIT8zAJr8K'

# Local Files
PRODUCT_DICTIONARY_FILE = 'product_dictionary.txt'
COOKIES_FILE = 'cookies.pkl'
RESTOCK_TRACKER_FILE = 'restock_tracker.pkl'

# Injects cookies manually in event of reCaptcha or similar obstacles
def inject_cookies(driver, url):
    driver.get(url)
    time.sleep(3)
    
    print("Injecting cookies...")
    for cookie in MANUAL_COOKIES:
        driver.add_cookie(cookie)

    driver.refresh()

# Loads cookies saved from previous session if available
# Returns:
#   True on successful load
#   False on failure to load
def load_cookies(driver):
    print("Loading cookies...")
    try:
        with open(COOKIES_FILE, "rb") as cookie_file:
            cookies = pickle.load(cookie_file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        print("Cookies loaded successfully.")
        driver.refresh()
        return True 
    except FileNotFoundError:
        print(f"Cookies file '{COOKIES_FILE}' not found. Manual login required.")
        return False
    except Exception as e:
        print(f"Unable to load cookies from '{COOKIES_FILE}': reason: {e}")
        return False
    
# Saves cookies from current session
def save_cookies(driver):
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "wb") as cookie_file:
        pickle.dump(cookies, cookie_file)
    print(f"Cookies saved to '{COOKIES_FILE}'.")

# Load product watchlist
def load_watchlist(file):
    product_watchlist = {}
    if os.path.exists(file):
        with open(file, 'r') as f:
            for line in f:
                product_name, alias = line.strip().split(',')
                product_watchlist[product_name] = alias
    return product_watchlist


# Load or initialize restock tracker
def load_restock_tracker():
    if os.path.exists(RESTOCK_TRACKER_FILE):
        with open(RESTOCK_TRACKER_FILE, 'rb') as file:
            return pickle.load(file)
    return {}

# Save restock tracker
def save_restock_tracker(data):
    with open(RESTOCK_TRACKER_FILE, 'wb') as file:
        pickle.dump(data, file)

restock_tracker = load_restock_tracker()

def send_discord_message(product_name, product_price, product_url):
    message = f"✔ In Stock: {product_name} - {product_price} ({product_url})"
    payload = {'content': message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, data=payload)
        response.raise_for_status()
        print(f"Message sent to Discord: {message}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

# Function to get total number of pages
def get_total_pages(driver):

    try:
        WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.wp-block-query-pagination-numbers')))
    except TimeoutException:
        return 1;

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    pagination_elements = soup.select('.page-numbers')

    if pagination_elements:
        page_numbers = []
        for element in pagination_elements:
            text = element.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))

        if page_numbers:
            return max(page_numbers)  # Get the highest page number

    return 1  # Default to 1 if no pagination is found

# Function to extract product details
def extract_product_details(product):
    name = product.find('h3', class_='has-text-align-center').get_text(strip=True)
    price = product.find('span', class_='woocommerce-Price-amount').get_text(strip=True)
    link = product.find('a')['href']
    return {'name': name, 'price': price, 'link': link}

# Function to iterate through products and check for restocks
def check_for_restock(driver, product_watchlist):
    global restock_tracker
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    product_items = soup.select("li.product")  # Select all product items

    for product in product_items:

        title_element = product.select_one("h3.wp-block-post-title a")
        product_name = title_element.get_text(strip=True) if title_element else "Unknown"
        product_url = title_element["href"] if title_element else "#"
        price_element = product.select_one(".woocommerce-Price-amount")
        product_price = price_element.get_text(strip=True) if price_element else "No Price"
        is_in_stock = "instock" in product.get("class", [])

        if is_in_stock:
            print(f"✔ In Stock: {product_name} - {product_price} ({product_url})")

            # Check if this product is in the watchlist
            for watch_product, alias in product_watchlist.items():
                if product_name.lower() in (watch_product.lower(), alias.lower()) or (watch_product.lower() in product_name.lower() or alias.lower() in product_name.lower()):
                    if product_name not in restock_tracker:
                        restock_tracker[product_name] = True
                        send_discord_message(product_name, product_price, product_url)
                    elif not restock_tracker[product_name]:
                        restock_tracker[product_name] = False
    save_restock_tracker(restock_tracker)

# Sequentially scrapes pages
def go_through_pages(driver):
    current_page = 1
    total_pages = get_total_pages(driver)
    print(f"Found {total_pages} pages of products.")
    
    while current_page <= total_pages:
        print(f"Scraping page {current_page}/{total_pages}...")
        driver.get(f"{SHOP_URL}{current_page}/")
        check_for_restock(driver, product_watchlist)
        current_page += 1

# Selenium WebDriver setup
def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)  # Use SafariDriver on macOS
    
    driver.maximize_window()

    #inject_cookies(driver, "https://pgbmemberpass.com/my-account/")
    #save_cookies(driver)
    
    driver.get(LOGIN_URL)

    # Handle cookies
    if not load_cookies(driver):
        if manual_discord_login(driver):
            save_cookies(driver)
        else:
            print("Discord login failed; resort to manual cookie modification for login")
            inject_cookies(driver, LOGIN_URL)
            save_cookies(driver)


    driver.get(SHOP_URL)
    return driver

# Automates manual discord login
#   Returns True for successful login
#   Returns False for failure
def manual_discord_login(driver):

    driver.get(LOGIN_URL)
    
    # Discord login button/widget
    try:
        discord_login_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "mo_btn-discord"))
        )
        time.sleep(0.5)
        discord_login_button.click()
        print("Clicked Discord Login button.")
    except:
        print("Discord Login button not found!")
        return False
    

    # Username input field
    username_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "uid_33"))
    )
    username_field.send_keys(DISCORD_USERNAME)

    # Password input field
    password_field = driver.find_element(By.ID, "uid_35")
    password_field.send_keys(DISCORD_PASSWORD)

    time.sleep(0.5)

    # Complete login
    login_button = driver.find_element(By.XPATH, "//button[contains(., 'Log In')]")
    login_button.click()
    print("Logged in successfully")

    # Find the scroll container and the initial button
    try:
        print("Attempting to find scroll container")
        time.sleep(1)

        scroll_container = driver.find_element(By.CLASS_NAME, "thin_d125d2")
        initial_button = driver.find_element(By.CSS_SELECTOR, '.button__201d5.lookFilled__201d5')

        if initial_button.is_displayed():
            print("Scrolling until authorize button found")

        # Scroll until the "Keep Scrolling..." button is replaced by the "Authorize" button
        scroll_attempts = 0
        while scroll_attempts < 3:
            scroll_attempts += 1

            # Scroll down inside the container
            driver.execute_script("arguments[0].scrollBy(0, arguments[0].scrollHeight);", scroll_container)

            # Brief w for the page to update
            time.sleep(1)
            
            # Check if the "Authorize" button is now updated
            try:
                authorize_button = driver.find_element(By.CSS_SELECTOR, '.action__3d3b0 button')
                if authorize_button.is_displayed():
                    authorize_button.click()
                    print("Discord login authorized")
                    return True
            except Exception as e:
                pass # "Authorize" button hasn't appeared yet, continue scrolling

    except NoSuchElementException:
        print("Discord login failed; likely Captcha")
        return False
    except Exception as e:
        print(f"Discord login failed; {e}")

# Main function to run the script
def main():
    # Read watchlist from product_dictionary.txt
    global product_watchlist
    product_watchlist = load_watchlist(PRODUCT_DICTIONARY_FILE)

    while True:
        # Setup driver and go through product pages
        driver = setup_driver()
        driver.get(SHOP_URL)
        go_through_pages(driver)
        driver.quit()

        # Wait for one hour before reloading
        print("Waiting for 1 hour...")
        time.sleep(3600)

if __name__ == '__main__':
    main()

