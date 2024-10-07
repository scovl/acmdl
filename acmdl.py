import requests
from bs4 import BeautifulSoup
import re
import os
import time

# Keyword for search
query = "Java nullpointer"
url_base = "https://dl.acm.org"
search_url = f"{url_base}/action/doSearch?AllField={query.replace(' ', '+')}"

# Headers to avoid being blocked (imitating a common browser)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Directory to save PDFs
os.makedirs("acm_pdfs", exist_ok=True)

try:
    # Making the search request on ACM
    response = requests.get(search_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # Getting the article links
    articles = soup.find_all("a", href=re.compile("^/doi/"))
    article_links = [url_base + article["href"] for article in articles]

    # Downloading PDFs
    for article_url in article_links:
        try:
            article_response = requests.get(article_url, headers=HEADERS)
            article_response.raise_for_status()
            article_soup = BeautifulSoup(article_response.content, "html.parser")

            # Finding the PDF link
            pdf_link = article_soup.find("a", href=re.compile("/doi/pdf/"))
            if pdf_link:
                pdf_url = url_base + pdf_link["href"]
                pdf_response = requests.get(pdf_url, headers=HEADERS)

                # Ignore PDFs that return 403 error or others
                if pdf_response.status_code == 200:
                    # Extracting the article title to use as file name
                    title_tag = article_soup.find("h1", class_="citation__title")
                    if title_tag:
                        title = title_tag.get_text(strip=True).replace('/', '-')
                        file_path = os.path.join("acm_pdfs", f"{title}.pdf")

                        # Saving the PDF
                        with open(file_path, "wb") as pdf_file:
                            pdf_file.write(pdf_response.content)
                        print(f"Downloaded: {title}")
                    else:
                        print(f"Title not found for article at: {article_url}")
                else:
                    print(f"Access denied to PDF at: {pdf_url}")
            else:
                print(f"PDF link not found at: {article_url}")

            # Pause to avoid too many requests in a short time
            time.sleep(1)

        except requests.RequestException as e:
            print(f"Error processing article {article_url}: {e}")
            continue

except requests.RequestException as e:
    print(f"Error accessing search page: {e}")
    if response.status_code == 403:
        print("Access denied to the search page. Check if you have proper access or try again later.")

# Usage instructions
if __name__ == "__main__":
    print("Usage: python acmdl.py")