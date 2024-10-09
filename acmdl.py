import os
import time
import logging
import requests
import toml
import io
import urllib.request
import threading
import keyboard
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PyPDF2 import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from TOML file
config = toml.load('config.toml')

# Keyword for search
query = config.get('query', 'Java nullpointer')
url_base = "https://dl.acm.org"
search_url = f"{url_base}/action/doSearch?AllField={query.replace(' ', '+')}"

# Directory to save PDFs
os.makedirs("acm_pdfs", exist_ok=True)

# Setting up Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Setting up requests session with retries
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
session.mount('https://', adapter)

# Thread stop event
stop_event = threading.Event()

def is_valid_pdf(content):
    try:
        pdf_reader = PdfReader(io.BytesIO(content))
        return len(pdf_reader.pages) > 0
    except Exception as e:
        logging.warning("Invalid PDF file: %s", e)
    return False

def process_article(article_url):
    if stop_event.is_set():
        return
    try:
        logging.info("Processing article: %s", article_url)

        # Check if the link is already a direct link to a PDF (e.g., /doi/epdf/ or /doi/pdf/)
        if "/doi/epdf/" in article_url or "/doi/pdf/" in article_url:
            pdf_url = article_url
            response = session.head(pdf_url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                return pdf_url
            else:
                logging.warning("PDF is not accessible (status code: %d), skipping: %s", response.status_code, pdf_url)
            return None

        driver.get(article_url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)  # Allow additional time for page to load completely

        # Check for access type: Public Access, Open Access, or Free Access
        try:
            access_type_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Public Access') or contains(text(), 'Open Access') or contains(text(), 'Free Access')]"))
            )
            access_type_text = access_type_element.text
        except TimeoutException:
            logging.info("Skipping article: Not Public, Open, or Free Access")
            return None

        if "Public Access" in access_type_text or "Open Access" in access_type_text or "Free Access" in access_type_text:
            try:
                pdf_link = get_pdf_link()
                if pdf_link:
                    pdf_url = pdf_link.get_attribute("href")
                    response = session.head(pdf_url, allow_redirects=True, timeout=10)
                    if response.status_code == 200:
                        return pdf_url
                    else:
                        logging.warning("PDF is not accessible (status code: %d), skipping: %s", response.status_code, pdf_url)
            except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
                logging.warning("PDF link not found at: %s", article_url)

    except (requests.RequestException, TimeoutException, WebDriverException) as e:
        logging.error("Error processing article %s: %s", article_url, e)
    return None

def get_pdf_link():
    try:
        return WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//a[@title='View PDF']")))
    except TimeoutException:
        e_reader_link = driver.find_element(By.XPATH, "//a[@aria-label='View online with eReader']")
        if e_reader_link:
            return e_reader_link
    return None

def download_pdf(article_url, pdf_url, progress_bar):
    try:
        driver.get(article_url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        title_tag = driver.find_element(By.TAG_NAME, "h1")
        title = title_tag.text.strip().replace('/', '-').replace('\\', '-').replace('"', '').replace("'", '')
        if not title:
            raise ValueError("Empty title extracted")
    except (NoSuchElementException, ValueError):
        title = f"article_{int(time.time())}"
    file_path = os.path.join("acm_pdfs", f"{title}.pdf")

    # Alternative download method using urllib
    try:
        logging.info("Attempting to download PDF using urllib: %s", pdf_url)
        urllib.request.urlretrieve(pdf_url, file_path)
        logging.info("Downloaded using urllib: %s", title)
    except Exception as e:
        logging.warning("Failed to download using urllib: %s", e)

    # Downloading the PDF content using requests
    pdf_response = session.get(pdf_url, stream=True)
    if pdf_response.status_code == 200:
        pdf_content = pdf_response.content
        if is_valid_pdf(pdf_content):
            with open(file_path, "wb") as pdf_file:
                pdf_file.write(pdf_content)
            logging.info("Downloaded: %s", title)
            progress_bar.update(1)
        else:
            logging.warning("The PDF is not valid, skipping: %s", pdf_url)
    else:
        logging.warning("Failed to download PDF, status code: %d, URL: %s", pdf_response.status_code, pdf_url)

def listen_for_exit():
    keyboard.wait('f1')
    logging.info("F1 pressed. Stopping all threads and exiting.")
    stop_event.set()

try:
    # Making the search request on ACM
    logging.info("Accessing search page...")
    driver.get(search_url)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Check if the IP address has been blocked
    if "Your IP Address has been blocked" in driver.page_source:
        logging.error("Your IP Address has been blocked. Please try using a VPN or wait for a while before trying again.")
    else:
        # Getting the article links
        articles = driver.find_elements(By.XPATH, "//a[contains(@href, '/doi/')]")
        article_links = [article.get_attribute("href") for article in articles]

        if not article_links:
            logging.warning("No articles found. Please check the query or the website structure.")

        # Start listening for F1 key to stop the process
        threading.Thread(target=listen_for_exit, daemon=True).start()

        # Processing articles sequentially and downloading only valid ones with progress bar
        pdf_urls = []
        for article_url in article_links:
            pdf_url = process_article(article_url)
            if pdf_url:
                pdf_urls.append((article_url, pdf_url))

        with tqdm(total=len(pdf_urls), desc="Downloading articles", unit="article") as progress_bar:
            for article_url, pdf_url in pdf_urls:
                download_pdf(article_url, pdf_url, progress_bar)

except TimeoutException as e:
    logging.error("Error accessing search page: %s", e)

finally:
    driver.quit()
    logging.info("Driver quit.")

# Usage instructions
if __name__ == "__main__":
    logging.info("Script executed. Check the console output for details on downloaded articles.")