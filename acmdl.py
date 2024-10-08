import os
import time
import logging
import requests
import toml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PyPDF2 import PdfReader
import io

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
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

def is_valid_pdf(content):
    try:
        pdf_reader = PdfReader(io.BytesIO(content))
        if len(pdf_reader.pages) > 0:
            return True
    except Exception as e:
        logging.warning("Invalid PDF file: %s", e)
    return False

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

        # Downloading PDFs
        for article_url in article_links:
            try:
                logging.info("Processing article: %s", article_url)
                driver.get(article_url)
                WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                # Adding an explicit wait for the PDF link to appear
                try:
                    # Locate the PDF download link based on the title attribute
                    pdf_link = None
                    try:
                        pdf_link = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//a[@title='View PDF']")))
                    except TimeoutException:
                        # If the 'View PDF' link is not found, try to find 'View online with eReader'
                        e_reader_link = driver.find_element(By.XPATH, "//a[@aria-label='View online with eReader']")
                        if e_reader_link:
                            pdf_link = e_reader_link

                    if pdf_link:
                        pdf_url = pdf_link.get_attribute("href")

                        # Checking if the PDF URL is accessible
                        response = session.head(pdf_url, allow_redirects=True, timeout=10)
                        if response.status_code != 200:
                            logging.warning("PDF is not accessible (status code: %d), skipping: %s", response.status_code, pdf_url)
                            continue

                        # Extracting the article title to use as file name
                        try:
                            title_tag = driver.find_element(By.TAG_NAME, "h1")
                            title = title_tag.text.strip().replace('/', '-').replace('\\', '-').replace('"', '').replace("'", '')
                            if not title:
                                raise ValueError("Empty title extracted")
                        except (NoSuchElementException, ValueError):
                            title = f"article_{int(time.time())}"
                        file_path = os.path.join("acm_pdfs", f"{title}.pdf")

                        # Downloading the PDF content using requests
                        pdf_response = session.get(pdf_url, stream=True)
                        if pdf_response.status_code == 200:
                            pdf_content = pdf_response.content
                            if is_valid_pdf(pdf_content):
                                with open(file_path, "wb") as pdf_file:
                                    pdf_file.write(pdf_content)
                                logging.info("Downloaded: %s", title)
                            else:
                                logging.warning("The PDF is not valid, skipping: %s", pdf_url)
                        else:
                            logging.warning("Failed to download PDF, status code: %d, URL: %s", pdf_response.status_code, pdf_url)

                except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
                    logging.warning("PDF link not found at: %s", article_url)

                # Pause to avoid too many requests in a short time
                time.sleep(5)

            except (requests.RequestException, TimeoutException, WebDriverException) as e:
                logging.error("Error processing article %s: %s", article_url, e)
                continue

except TimeoutException as e:
    logging.error("Error accessing search page: %s", e)

finally:
    driver.quit()
    logging.info("Driver quit.")

# Usage instructions
if __name__ == "__main__":
    logging.info("Script executed. Check the console output for details on downloaded articles.")