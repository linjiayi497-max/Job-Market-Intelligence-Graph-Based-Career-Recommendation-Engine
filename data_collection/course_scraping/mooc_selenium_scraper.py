#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MOOC (中国大学MOOC/iCourse163) Course Scraper — Selenium Version

Scrapes course listings from the iCourse163 MOOC platform using Selenium
WebDriver for keyword-based searches with automatic pagination.

Features:
- Keyword-based course search via browser automation
- Extracts: title, university, instructor, description, start date, enrollment
- Automatic pagination handling
- CSV output per keyword
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER
import time
import csv
import os
import logging


class MoocSpider:
    """Selenium-based scraper for iCourse163 MOOC platform."""

    def __init__(self, keyword: str):
        """
        Initialize the MOOC spider.

        Args:
            keyword: Search keyword for course discovery
        """
        self.keyword = keyword

        # Suppress verbose Selenium logs
        LOGGER.setLevel(logging.WARNING)

        chrome_options = Options()
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        self.driver = webdriver.Chrome(options=chrome_options)
        self.base_url = "https://www.icourse163.org/search.htm?search={}#/"

        # Output directory setup
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, 'data')
        self.output_file = None
        os.makedirs(self.data_dir, exist_ok=True)

    def setup_output_file(self):
        """Create output CSV file with header row."""
        self.output_file = os.path.join(self.data_dir, f"mooc_courses_{self.keyword}.csv")
        with open(self.output_file, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['course_title', 'university', 'instructor', 'description', 'start_date', 'enrollment'])

    def save_course_to_csv(self, course_data: list):
        """Append a single course record to the CSV file."""
        with open(self.output_file, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(course_data)

    def extract_course_info(self, course) -> list:
        """
        Extract structured information from a single course element.

        Returns:
            List of [title, university, instructor, description, start_date, enrollment]
        """
        try:
            title = course.find_element(By.CLASS_NAME, '_1vfZ-').text.strip() if course.find_elements(By.CLASS_NAME, '_1vfZ-') else ''
            school = course.find_element(By.CLASS_NAME, '_3vJDG').text.strip() if course.find_elements(By.CLASS_NAME, '_3vJDG') else ''
            instructor = course.find_element(By.CLASS_NAME, '_3t_C8').text.strip() if course.find_elements(By.CLASS_NAME, '_3t_C8') else ''
            description = course.find_element(By.CLASS_NAME, '_3JEMz').text.strip() if course.find_elements(By.CLASS_NAME, '_3JEMz') else ''
            start_time = course.find_element(By.CLASS_NAME, 'NOdDs').text.strip() if course.find_elements(By.CLASS_NAME, 'NOdDs') else ''
            participants = course.find_element(By.CLASS_NAME, '_CWjg').text.strip() if course.find_elements(By.CLASS_NAME, '_CWjg') else ''
            return [title, school, instructor, description, start_time, participants]
        except Exception as e:
            print(f"Error extracting course info: {str(e)}")
            return None

    def print_course_info(self, index: int, course_data: list):
        """Print course information to console."""
        if course_data:
            print(f"Course {index}:")
            print(f"  Title: {course_data[0]}")
            print(f"  University: {course_data[1]}")
            print(f"  Instructor: {course_data[2]}")
            print(f"  Start Date: {course_data[4]}")
            print(f"  Enrollment: {course_data[5]}")
            print("-" * 50)

    def crawl(self):
        """Execute the full crawling workflow with automatic pagination."""
        try:
            self.setup_output_file()
            self.driver.get(self.base_url.format(self.keyword))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, '_3NYsM'))
            )

            while True:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, '_3NYsM'))
                    )
                    courses = self.driver.find_elements(By.CLASS_NAME, '_3NYsM')

                    for index, course in enumerate(courses, start=1):
                        course_data = self.extract_course_info(course)
                        if course_data:
                            self.print_course_info(index, course_data)
                            self.save_course_to_csv(course_data)

                    # Handle pagination
                    next_buttons = self.driver.find_elements(By.CLASS_NAME, 'ant-pagination-item-link')
                    if next_buttons:
                        next_button = next_buttons[-1]
                        if not next_button.get_attribute('disabled'):
                            next_button.click()
                            time.sleep(2)
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_all_elements_located((By.CLASS_NAME, '_3NYsM'))
                            )
                        else:
                            print("Reached the last page.")
                            break
                    else:
                        print("No pagination buttons found.")
                        break

                except Exception as e:
                    print(f"Page processing error: {str(e)}")
                    break

            print(f"\nData saved to: {self.output_file}")

        except Exception as e:
            print(f"Crawling error: {str(e)}")

    def close(self):
        """Close the browser session."""
        if self.driver:
            self.driver.quit()


def main():
    """Main entry point — scrape courses for a given keyword."""
    keyword = "new energy"  # Modify keyword as needed
    spider = MoocSpider(keyword)
    try:
        spider.crawl()
        input("Press Enter to close browser...")
    finally:
        spider.close()


if __name__ == "__main__":
    main()
