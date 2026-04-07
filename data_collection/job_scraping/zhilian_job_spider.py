#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zhilian (智联招聘) Job Listing Spider

Web scraper for collecting job listing data from Zhilian Recruitment platform.
Uses Selenium WebDriver to navigate search results across provinces/cities
with configurable keyword lists and progress tracking.

Features:
- Multi-keyword, multi-city scraping with progress persistence
- Anti-detection Chrome configuration
- Automatic pagination handling
- CSV output with daily date stamps
"""

import csv
import os
import time
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import pickle

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from lxml import etree
from colorama import Fore, Style

# Province/City codes for Zhilian search API
PROVINCES_CODE = {
    '北京': '530', '天津': '531', '河北': '532', '山西': '533', '内蒙古': '534',
    '辽宁': '535', '吉林': '536', '黑龙江': '537', '上海': '538', '江苏': '539',
    '浙江': '540', '安徽': '541', '福建': '542', '江西': '543', '山东': '544',
    '河南': '545', '湖北': '546', '湖南': '547', '广东': '548', '广西': '549',
    '海南': '550', '重庆': '551', '四川': '552', '贵州': '553', '云南': '554',
    '西藏': '555', '陕西': '556', '甘肃': '557', '青海': '558', '宁夏': '559',
    '新疆': '560', '香港': '561', '澳门': '562', '台湾': '563'
}

# Directory configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
PROGRESS_DIR = os.path.join(SCRIPT_DIR, 'progress')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data', 'JobPosting', 'ZhiLian')
os.makedirs(DATA_DIR, exist_ok=True)


class ZhilianSpider:
    """Web spider for Zhilian job platform."""

    def __init__(self):
        """Initialize spider with Chrome WebDriver."""
        self.driver = self._init_chrome_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def _init_chrome_driver(self) -> Chrome:
        """Initialize Chrome browser with anti-detection settings."""
        options = ChromeOptions()

        # Disable automation detection
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)

        # Log level and performance settings
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-gpu-blocklist')
        options.add_argument('--disable-infobars')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-notifications')
        options.page_load_strategy = 'normal'

        try:
            driver = Chrome(options=options)
            driver.implicitly_wait(10)
            print(f"{Fore.GREEN}[INFO] Browser initialized successfully{Style.RESET_ALL}")
            return driver
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Browser initialization failed: {str(e)}{Style.RESET_ALL}")
            raise

    def login(self, url: str) -> None:
        """Navigate to login page and wait for manual login."""
        self.driver.get(url)
        print(f"{Fore.GREEN}[INFO] Please log in manually, then press Enter to continue...{Style.RESET_ALL}", end='')
        input()

    def search_jobs(self, keywords: List[str], cities: List[str]) -> None:
        """
        Search and scrape job listings for given keywords across cities.

        Args:
            keywords: List of search keywords (e.g., job titles, skills)
            cities: List of province/city names to search in
        """
        for keyword in keywords:
            print(f"{Fore.GREEN}[INFO] Starting to scrape keyword: {keyword}{Style.RESET_ALL}")
            logging.info(f"Starting keyword: {keyword}")

            # Load progress for resumable scraping
            completed_cities = load_progress(keyword)
            if completed_cities:
                print(f"{Fore.GREEN}[INFO] Resuming from previous progress. Completed: {', '.join(completed_cities)}{Style.RESET_ALL}")

            for city in cities:
                if city in completed_cities:
                    print(f"{Fore.GREEN}[INFO] Skipping completed city: {city}{Style.RESET_ALL}")
                    continue

                if city not in PROVINCES_CODE:
                    print(f"{Fore.YELLOW}[WARNING] Invalid city: {city}{Style.RESET_ALL}")
                    logging.warning(f"Invalid city: {city}")
                    continue

                url = f'https://sou.zhaopin.com/?jl={PROVINCES_CODE[city]}&kw={keyword}&p=1'
                print(f"{Fore.GREEN}[INFO] Scraping {city} - {keyword}{Style.RESET_ALL}", end='', flush=True)
                logging.info(f"Starting city: {city}")

                try:
                    self.driver.get(url)
                    self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'sou-main__list')))

                    if not self.driver.find_elements(By.CLASS_NAME, 'positionlist'):
                        print()
                        print(f"{Fore.YELLOW}[WARNING] No {keyword} jobs found in {city}{Style.RESET_ALL}")
                        logging.warning(f"No {keyword} jobs found in {city}")
                        completed_cities.append(city)
                        save_progress(keyword, completed_cities)
                        continue

                    self._parse_job_listings(keyword, city)

                    completed_cities.append(city)
                    save_progress(keyword, completed_cities)
                    logging.info(f"Completed city: {city}")

                except Exception as e:
                    print(f"{Fore.RED}[ERROR] Error scraping {city}: {str(e)}{Style.RESET_ALL}")
                    logging.error(f"Error scraping city {city}: {str(e)}")
                    continue

    def _parse_job_listings(self, keyword: str, city: str) -> None:
        """Parse job listing elements from the current page."""
        html = self.driver.page_source
        root = etree.HTML(html)
        listings = root.xpath('//div[@class="positionlist"]')

        if not listings:
            return

        self._parse_listing(listings[0], keyword, city)
        self._handle_pagination(keyword, city)

    def _parse_listing(self, listing, keyword: str, city: str) -> None:
        """Extract structured data from a single job listing element."""
        data = {
            'search_keyword': keyword,
            'industry': self._get_text(listing, '//div[@class="companyinfo__tag"]/div[3]/text()'),
            'job_title': self._get_text(listing, '//a[contains(@class, "jobinfo__name")]/text()'),
            'company_name': self._get_attr(listing, '//a[contains(@class, "companyinfo__name")]/@title'),
            'salary': self._get_text(listing, '//p[@class="jobinfo__salary"]/text()'),
            'province': city,
            'city': self._get_text(listing, '//img[@class="jobinfo__other-info-location-image"]/../span/text()'),
            'experience': self._get_text(listing, '//div[@class="jobinfo__other-info"]/div[2]/text()'),
            'education': self._get_text(listing, '//div[@class="jobinfo__other-info"]/div[3]/text()'),
            'company_type': self._get_text(listing, '//div[@class="companyinfo__tag"]/div[1]/text()'),
            'company_size': self._get_text(listing, '//div[@class="companyinfo__tag"]/div[2]/text()'),
            'detail_url': self._get_attr(listing, '//a[contains(@class, "jobinfo__name")]/@href')
        }
        self._write_to_csv(data, keyword)

    @staticmethod
    def _get_text(element, xpath: str) -> str:
        """Extract text content from an XPath match."""
        result = element.xpath(xpath)
        return result[0].strip() if result else ''

    @staticmethod
    def _get_attr(element, xpath: str) -> str:
        """Extract attribute value from an XPath match."""
        result = element.xpath(xpath)
        return result[0] if result else ''

    def _handle_pagination(self, keyword: str, city: str) -> None:
        """Handle page navigation, recursively parsing subsequent pages."""
        try:
            next_buttons = self.driver.find_elements(By.XPATH, '//a[@class="btn soupager__btn"]')
            if not next_buttons or 'disabled' in next_buttons[0].get_attribute('class'):
                print(f"{Fore.GREEN}  -- completed{Style.RESET_ALL}")
                return

            next_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//a[@class="btn soupager__btn"]'))
            )
            self.driver.execute_script('arguments[0].click()', next_button)
            time.sleep(1.5)
            self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'sou-main__list')))
            self._parse_job_listings(keyword, city)

        except Exception as e:
            if "element click intercepted" in str(e).lower():
                print(f"{Fore.RED}[ERROR] Click intercepted, retrying...{Style.RESET_ALL}")
                time.sleep(1)
                self._handle_pagination(keyword, city)
            else:
                print(f"{Fore.RED}[ERROR] Pagination error: {str(e)}{Style.RESET_ALL}")

    @staticmethod
    def _write_to_csv(data: Dict, keyword: str) -> None:
        """Append job data to a date-stamped CSV file."""
        today = datetime.now().strftime('%Y%m%d')
        file_path = os.path.join(DATA_DIR, f'ZL_{today}_{keyword}.csv')

        has_header = os.path.exists(file_path)
        with open(file_path, 'a', encoding='utf-8_sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not has_header:
                writer.writeheader()
            writer.writerow(data)

    def close(self) -> None:
        """Close the browser session."""
        self.driver.quit()


# ========== Progress Management ==========

def setup_logging():
    """Configure file-based logging."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'ZL_SL_{datetime.now().strftime("%Y%m%d")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file, encoding='utf-8')],
    )


def save_progress(keyword: str, completed_cities: List[str]) -> None:
    """Persist scraping progress to a pickle file for resumability."""
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    progress_file = os.path.join(PROGRESS_DIR, f'ZL_SP_{keyword}.pkl')
    with open(progress_file, 'wb') as f:
        pickle.dump(completed_cities, f)
    logging.info(f"Progress saved: {progress_file}")


def load_progress(keyword: str) -> List[str]:
    """Load previously saved scraping progress."""
    progress_file = os.path.join(PROGRESS_DIR, f'ZL_SP_{keyword}.pkl')
    if os.path.exists(progress_file):
        with open(progress_file, 'rb') as f:
            completed_cities = pickle.load(f)
        logging.info(f"Progress loaded: {progress_file}")
        return completed_cities
    return []


def load_keywords_from_file(file_path: str) -> List[str]:
    """Load search keywords from a text file (one keyword per line)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
            if not keywords:
                print(f"{Fore.RED}[ERROR] Keywords file is empty{Style.RESET_ALL}")
                return []
            return keywords
    except FileNotFoundError:
        print(f"{Fore.RED}[ERROR] Keywords file not found: {file_path}{Style.RESET_ALL}")
        return []


def get_keywords() -> List[str]:
    """Prompt user to select keyword source."""
    print("Select keyword source:")
    print("1. Use built-in keyword list")
    print("2. Read from keywords.txt file")
    choice = input("Enter choice (1 or 2): ")

    default_keywords = [
        'carbon trading', 'carbon management', 'energy storage', 'battery',
        'materials', 'ESG', 'energy', 'environmental', 'low-carbon',
        'carbon emission', 'carbon trading', 'carbon business'
    ]

    if choice == '2':
        return load_keywords_from_file(os.path.join(SCRIPT_DIR, 'keywords.txt'))
    return default_keywords


def main():
    """Main entry point."""
    setup_logging()
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PROGRESS_DIR, exist_ok=True)

    keywords = get_keywords()
    if not keywords:
        print(f"{Fore.RED}[ERROR] No valid keywords, exiting.{Style.RESET_ALL}")
        return

    cities = list(PROVINCES_CODE.keys())

    spider = ZhilianSpider()
    try:
        spider.login('https://passport.zhaopin.com/login')
        spider.search_jobs(keywords, cities)
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}[WARNING] User interrupted, exiting...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error: {str(e)}{Style.RESET_ALL}")
        raise
    finally:
        spider.close()
        print(f"{Fore.GREEN}[INFO] Spider task completed, browser closed.{Style.RESET_ALL}")


if __name__ == '__main__':
    main()
