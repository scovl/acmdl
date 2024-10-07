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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

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

try:
    # Making the search request on ACM
    logging.info("Accessing search page...")
    driver.get(search_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

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
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                # Finding the PDF link
                try:
                    pdf_link = driver.find_element(By.XPATH, "//a[contains(@href, '/doi/pdf/')]")
                    pdf_url = pdf_link.get_attribute("href")
                    pdf_response = requests.get(pdf_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                    })

                    # Ignore PDFs that return 403 error or others
                    if pdf_response.status_code == 200:
                        # Extracting the article title to use as file name
                        try:
                            title_tag = driver.find_element(By.CLASS_NAME, "citation__title")
                            title = title_tag.text.strip().replace('/', '-')
                        except NoSuchElementException:
                            title = "unknown_title"
                        file_path = os.path.join("acm_pdfs", f"{title}.pdf")

                        # Saving the PDF
                        with open(file_path, "wb") as pdf_file:
                            pdf_file.write(pdf_response.content)
                        logging.info("Downloaded: %s", title)
                    else:
                        logging.warning("Access denied to PDF at: %s", pdf_url)
                except (TimeoutException, NoSuchElementException):
                    logging.warning("PDF link not found at: %s", article_url)

                # Pause to avoid too many requests in a short time
                time.sleep(10)

            except (requests.RequestException, TimeoutException) as e:
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