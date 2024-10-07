# acmdl

acmdl is a Python script that scrapes the ACM Digital Library for articles based on a specified keyword and downloads the corresponding PDF files. The script uses Selenium for web scraping and is configured via a `config.toml` file.

## Features
- Searches for articles in the ACM Digital Library based on a keyword.
- Downloads the PDFs of the articles found.
- Uses Selenium to navigate through the ACM website.
- Configurable keyword via `config.toml` file.

## Requirements
- Python 3.6+
- Google Chrome browser
- ChromeDriver
- The following Python packages:
  - `selenium`
  - `requests`
  - `webdriver-manager`
  - `toml`

## Installation
1. Clone this repository.
2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install the required dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Alternative: Use `uv` for Dependency Management
We recommend using [uv](https://github.com/astral-sh/uv), an extremely fast Python package and project manager written in Rust, to manage dependencies. `uv` can replace tools like `pip`, `pip-tools`, `pipx`, `poetry`, and `virtualenv`, offering significant performance improvements and better project management.

To install `uv`:

- On macOS and Linux:
  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- On Windows:
  ```sh
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- With `pip`:
  ```sh
  pip install uv
  ```

To manage dependencies using `uv`, navigate to your project directory and run:
```sh
uv init example
uv add selenium requests webdriver-manager toml
```

## Configuration
Create a `config.toml` file in the root directory with the following content:
```toml
query = "Java nullpointer"
```
This file allows you to specify the keyword used for searching articles in the ACM Digital Library.

## Usage
Run the script using:
```sh
python acmdl.py
```
The script will search for articles based on the keyword specified in `config.toml` and attempt to download the corresponding PDFs.

## Important Note on IP Blocking
The ACM Digital Library may block your IP address if it detects too many requests in a short period. This could result in your IP being blocked for up to a week. To avoid this, consider adding longer delays between requests or using a VPN to rotate your IP address.

## Disclaimer
Use this script responsibly. The ACM Digital Library is a paid service, and excessive scraping may violate its terms of service.
