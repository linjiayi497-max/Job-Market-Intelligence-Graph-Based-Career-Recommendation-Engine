#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liepin (猎聘网) Job Listing Spider

Web scraper for collecting job listing data from Liepin recruitment platform.
Scrapes by keyword + city district, with anti-detection measures and progress tracking.

Features:
- District-level granularity for comprehensive coverage
- Random delays and user-agent rotation for anti-detection
- JSON-based city/district code mapping
- Progress persistence per keyword
- CSV output with daily timestamps
"""

import csv
import os
import time
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from colorama import init, Fore, Style
import pickle
from pathlib import Path
init()

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from lxml import etree
import argparse
import logging

# Spider configuration
CONFIG = {
    'max_pages': 20,
    'max_retries': 3,
    'min_delay': 1,
    'max_delay': 3,
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
}

# Directory configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
PROGRESS_DIR = os.path.join(SCRIPT_DIR, 'progress')
PROVINCES_CODE_DIR = os.path.join(SCRIPT_DIR, 'province_city_code')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data', 'JobPosting', 'LiePin')


class LiePinSpider:
    """Web spider for the Liepin job recruitment platform."""

    def __init__(self):
        """Initialize spider with Chrome WebDriver."""
        self.driver = self._init_chrome_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.current_retry = 0

    def _init_chrome_driver(self) -> Chrome:
        """Initialize Chrome with anti-detection and performance settings."""
        options = ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--start-maximized')
        options.add_argument(f'--user-agent={random.choice(CONFIG["user_agents"])}')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.page_load_strategy = 'normal'

        try:
            driver = Chrome(options=options)
            # Override navigator.webdriver to avoid detection
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            })
            driver.implicitly_wait(random.uniform(5, 10))
            print(f"{Fore.GREEN}[INFO] Browser initialized successfully{Style.RESET_ALL}")
            return driver
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Browser initialization failed: {str(e)}{Style.RESET_ALL}")
            raise

    def search_jobs(self, url_items: List[Dict]) -> None:
        """Scrape job listings from a list of URL items."""
        for url_item in url_items:
            url = url_item['url']
            keyword = url_item['keyword']
            district = url_item['district']

            self.current_retry = 0
            while self.current_retry < CONFIG['max_retries']:
                try:
                    time.sleep(random.uniform(CONFIG['min_delay'], CONFIG['max_delay']))
                    print(f"{Fore.GREEN}[INFO] Scraping {district} - {keyword} (attempt {self.current_retry + 1}/{CONFIG['max_retries']}){Style.RESET_ALL}")
                    self.driver.get(url)

                    # Random scroll to mimic human behavior
                    for _ in range(random.randint(2, 4)):
                        self.driver.execute_script(f"window.scrollBy(0, {random.randint(200, 500)});")
                        time.sleep(random.uniform(0.5, 1.5))

                    html = self.driver.page_source

                    # Check for anti-bot detection
                    if '<span class="title">账号行为异常</span>' in html:
                        print(f"{Fore.RED}[WARNING] Anti-bot detected. Please resolve and press Enter...{Style.RESET_ALL}")
                        input()
                        return

                    root = etree.HTML(html)
                    if not root.xpath('//div[@class="job-list-box"]'):
                        print(f"{Fore.YELLOW}[WARNING] No {keyword} jobs in {district}{Style.RESET_ALL}")
                        break

                    self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'job-list-box')))
                    keyword = url.split('&key=')[1].split('&')[0]
                    self._parse_job_listings(keyword)
                    break

                except Exception as e:
                    self.current_retry += 1
                    print(f"{Fore.RED}[ERROR] Scraping error (attempt {self.current_retry}/{CONFIG['max_retries']}): {str(e)}{Style.RESET_ALL}")
                    if self.current_retry < CONFIG['max_retries']:
                        wait_time = random.uniform(5, 10)
                        time.sleep(wait_time)

    def _parse_job_listings(self, keyword: str) -> None:
        """Parse all job listings on the current page."""
        try:
            time.sleep(random.uniform(CONFIG['min_delay'], CONFIG['max_delay']))
            html = self.driver.page_source
            root = etree.HTML(html)

            job_list = root.xpath('//div[@class="job-list-box"]')
            if not job_list:
                return

            job_elements = job_list[0].xpath('./div')
            print(f"{Fore.GREEN}[INFO] Found {len(job_elements)} job listings{Style.RESET_ALL}")

            for job in job_elements:
                try:
                    data = {
                        'job_title': self._get_text(job, './/div[@class="jsx-2387891236 job-title-box"]/div[@title]/text()'),
                        'salary': self._get_text(job, './/span[@class="jsx-2387891236 job-salary"]/text()'),
                        'city': self._get_text(job, './/div[@class="jsx-2387891236 job-dq-box"]/span[@class="jsx-2387891236 ellipsis-1"]/text()'),
                        'company_name': self._get_text(job, './/span[@class="jsx-2387891236 company-name ellipsis-1"]/text()'),
                        'industry': self._get_text(job, './/div[@class="jsx-2387891236 company-tags-box ellipsis-1"]/span[1]/text()'),
                        'detail_url': self._get_attr(job, './/a[contains(@class, "jsx-2387891236")]/@href'),
                    }
                    for key, value in data.items():
                        data[key] = value.strip() if value else "Unknown"
                    self._write_to_csv(data, keyword)
                except Exception as e:
                    print(f"{Fore.RED}[ERROR] Error parsing job: {str(e)}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}[ERROR] Error parsing listings: {str(e)}{Style.RESET_ALL}")

    @staticmethod
    def _get_text(element, xpath: str) -> str:
        result = element.xpath(xpath)
        return result[0].strip() if result else ''

    @staticmethod
    def _get_attr(element, xpath: str) -> str:
        result = element.xpath(xpath)
        return result[0] if result else ''

    @staticmethod
    def _write_to_csv(data: Dict, keyword: str) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        today = datetime.now().strftime('%Y%m%d')
        file_path = os.path.join(DATA_DIR, f'LP_{today}_{keyword}.csv')
        has_header = os.path.exists(file_path)
        with open(file_path, 'a', encoding='utf-8_sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not has_header:
                writer.writeheader()
            writer.writerow(data)

    def close(self) -> None:
        self.driver.quit()


# ========== Helper Functions ==========

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'LP_SL_{datetime.now().strftime("%Y%m%d")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file, encoding='utf-8')],
    )


def save_progress(keyword: str, completed_urls: List[str]):
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    progress_file = os.path.join(PROGRESS_DIR, f'LP_SP_{keyword}.pkl')
    with open(progress_file, 'wb') as f:
        pickle.dump(completed_urls, f)


def load_progress(keyword: str) -> List[str]:
    progress_file = os.path.join(PROGRESS_DIR, f'LP_SP_{keyword}.pkl')
    if os.path.exists(progress_file):
        with open(progress_file, 'rb') as f:
            return pickle.load(f)
    return []


def load_city_dq_codes(cities: List[str]) -> Dict:
    """Load city and district codes from JSON mapping file."""
    file_path = os.path.join(PROVINCES_CODE_DIR, 'liepin_city_diqu_code_all.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            city_data = json.load(f)
        district_codes = {}
        for city_info in city_data:
            city_name = city_info['city']['name']
            if city_name not in cities:
                continue
            city_code = city_info['city']['code']
            if city_info['districts']:
                for district in city_info['districts']:
                    district_codes[district['name']] = {
                        'city_code': city_code,
                        'city_name': city_name,
                        'district_code': district['code']
                    }
        return district_codes
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to load city codes: {str(e)}{Style.RESET_ALL}")
        return {}


def generate_urls(district_codes: Dict, keyword: str) -> List[Dict]:
    """Generate search URLs for all districts under a keyword."""
    results = []
    for idx, (district_name, codes) in enumerate(district_codes.items(), 1):
        results.append({
            'url_index': idx,
            'keyword': keyword,
            'district': district_name,
            'url': f'https://www.liepin.com/zhaopin/?city={codes["city_code"]}&dq={codes["district_code"]}&key={keyword}&currentPage=20'
        })
    print(f"{Fore.GREEN}[INFO] Generated {len(results)} search URLs{Style.RESET_ALL}")
    return results


def main():
    """Main entry point."""
    setup_logging()
    cities = ['北京', '上海', '广州', '深圳', '天津', '重庆',
              '杭州', '南京', '武汉', '成都', '西安', '苏州']
    keywords = ['carbon trading', 'energy storage', 'ESG', 'low-carbon', 'new energy']

    spider = LiePinSpider()
    try:
        spider.driver.get(f'https://c.liepin.com/?time={int(time.time() * 1000)}')
        print(f"{Fore.GREEN}[INFO] Please login and press Enter to continue...{Style.RESET_ALL}")
        input()

        city_dq_codes = load_city_dq_codes(cities)
        for keyword in keywords:
            logging.info(f"Starting keyword: {keyword}")
            url_items = generate_urls(city_dq_codes, keyword)
            completed_urls = load_progress(keyword)
            url_items = [item for item in url_items if item['url'] not in completed_urls]
            if not url_items:
                continue
            for url_item in url_items:
                try:
                    spider.search_jobs([url_item])
                    completed_urls.append(url_item['url'])
                    save_progress(keyword, completed_urls)
                except Exception as e:
                    logging.error(f"URL scraping failed: {url_item['url']}: {str(e)}")
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}[WARNING] User interrupted.{Style.RESET_ALL}")
    finally:
        spider.close()
        print(f"{Fore.GREEN}[INFO] Spider completed.{Style.RESET_ALL}")


if __name__ == '__main__':
    main()
