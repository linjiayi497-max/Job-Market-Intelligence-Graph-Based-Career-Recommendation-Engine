#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MOOC (中国大学MOOC/iCourse163) Course Scraper — API Version

Scrapes course data from iCourse163 using the platform's internal RPC API.
Collects course metadata (name, university, enrollment) and fetches full
course descriptions from individual course pages.

Features:
- API-based scraping (faster than Selenium, no browser needed)
- Automatic pagination through all result pages
- Fetches course description from individual pages via BeautifulSoup
- Deduplication by course ID
- XLSX output per keyword
"""

import requests
import time
import os
import json
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd


def get_mooc_list(keyword: str, cookies: dict, headers: dict, params: dict, data: dict) -> list:
    """
    Fetch MOOC course listings via the iCourse163 search API.

    Args:
        keyword: Search keyword
        cookies: Session cookies for authentication
        headers: HTTP request headers
        params: URL query parameters
        data: POST body data

    Returns:
        List of course info dictionaries
    """
    response = requests.post(
        'https://www.icourse163.org/web/j/mocSearchBean.searchCourse.rpc',
        params=params, cookies=cookies, headers=headers, data=data,
    )

    if response is None or response.status_code != 200:
        print(f"Request failed, status: {response.status_code if response else 'No response'}")
        return []

    try:
        pages = response.json()['result']['query']['totlePageCount']
    except (KeyError, TypeError):
        print(f"No courses found for keyword, skipping.")
        return []

    print(f"Total pages: {pages}")
    course_info = []

    for page in range(1, pages + 1):
        data2 = {
            'mocCourseQueryVo': f'{{"keyword":"{keyword}","pageIndex":{page},"highlight":true,"orderBy":0,"stats":30,"pageSize":20}}',
        }
        response = requests.post(
            'https://www.icourse163.org/web/j/mocSearchBean.searchCourse.rpc',
            params=params, cookies=cookies, headers=headers, data=data2
        ).json()

        course_list = response['result']['list']
        if not course_list:
            print(f"No courses found on page {page}")
            return []

        print(f"Fetched page {page} course listings")

        for course in course_list:
            if (course and isinstance(course, dict) and
                'mocCourseCard' in course and
                isinstance(course.get('mocCourseCard'), dict) and
                'mocCourseCardDto' in course['mocCourseCard']):

                dto = course['mocCourseCard']['mocCourseCardDto']
                if (isinstance(dto, dict) and 'name' in dto and
                    'schoolPanel' in dto and 'termPanel' in dto):

                    school_short = dto['schoolPanel'].get('shortName', '')
                    if school_short and school_short.strip():
                        course_id = dto['termPanel'].get('courseId')
                        if course_id:
                            course_info.append({
                                'url_info': f"{school_short}-{course_id}",
                                'course_id': str(course_id),
                                'course_name': dto['name'],
                                'school_name': dto['schoolPanel'].get('name', ''),
                                'enroll_count': str(dto['termPanel'].get('enrollCount', 0)),
                            })

    return course_info


def get_course_content(url: str) -> str:
    """
    Fetch the course description from an individual course page.

    Args:
        url: Full URL to the course page

    Returns:
        Course description text, or error message
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        content_section = soup.find('div', {'id': 'content-section', 'class': 'm-infomation_content-section'})
        if content_section:
            return content_section.get_text()
        return "Course description not found"
    except Exception as e:
        print(f"Error fetching course content: {e}")
        return "Failed to fetch content"


def clean_text(text: str) -> str:
    """Remove non-printable characters from text."""
    return ''.join(c for c in text if c.isprintable())


def save_to_xlsx(keyword: str, course_info: list, output_path: str):
    """
    Fetch course descriptions and save all data to an XLSX file.

    Args:
        keyword: Search keyword used
        course_info: List of course info dictionaries
        output_path: Output XLSX file path
    """
    data_list = []

    for info in tqdm(course_info, desc='Processing courses', colour='green'):
        try:
            content = get_course_content(
                f"https://www.icourse163.org/course/{info['url_info']}"
            ).replace('spContent=', '')

            enroll = info.get('enroll_count', 0) or 0

            data_list.append({
                'search_keyword': keyword,
                'course_id': str(info.get('course_id', '')),
                'course_name': str(info.get('course_name', '')),
                'university': str(info.get('school_name', '')),
                'enrollment': str(enroll),
                'course_code': str(info.get('url_info', '')),
                'course_content': clean_text(content)
            })
        except Exception as e:
            print(f"Error processing course: {e}")

    df = pd.DataFrame(data_list)
    df = df.drop_duplicates(subset='course_code', keep='first')
    df.to_excel(output_path, index=False, engine='openpyxl')


if __name__ == '__main__':
    # NOTE: You need to provide your own session cookies, headers, and params
    # by creating a `para.py` file with the following variables:
    #   cookies, headers, params, data
    # These can be captured from browser DevTools (Network tab) when logged in.

    try:
        import para
        cookies = para.cookies
        headers = para.headers
        params = para.params
        data = para.data
    except ImportError:
        print("ERROR: Please create a para.py file with cookies, headers, params, and data.")
        print("Capture these from your browser DevTools (Network tab) while logged in to iCourse163.")
        exit(1)

    # Example keyword list — customize as needed
    keywords = [
        'machine learning', 'data science', 'artificial intelligence',
        'new energy', 'environmental engineering', 'carbon management'
    ]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'data')
    os.makedirs(output_dir, exist_ok=True)

    for keyword in keywords:
        mocCourseQueryVo = json.loads(data['mocCourseQueryVo'])
        mocCourseQueryVo['keyword'] = keyword
        data['mocCourseQueryVo'] = json.dumps(mocCourseQueryVo)

        output_path = os.path.join(output_dir, f'mooc_course_info_{keyword}.xlsx')

        if os.path.exists(output_path):
            print(f"File exists, skipping keyword: {keyword}")
            continue

        print(f"Fetching MOOC courses for keyword: {keyword}")
        course_info = get_mooc_list(keyword, cookies, headers, params, data)
        if not course_info:
            print(f"No courses found for '{keyword}', skipping.")
            continue
        save_to_xlsx(keyword, course_info, output_path)
        print(f"Saved course data for keyword: {keyword}")
