import os
import re
from browser import driver, whitelist
import time
import yaml

from detector.notifier import show_warning
from detector.nsfw import extract_text_from_html, is_nsfw_text
from browser.devtools import get_tabs_from_devtools

def is_tab_open(tab_handle):
    return tab_handle in driver.window_handles


def update_tab_urls(opened_tabs, not_found_tabs):
    devtools_tabs = get_tabs_from_devtools()
    for tab in devtools_tabs:
        tab_id = tab.get("id")
        page_url = tab.get("url")

        if tab_id and page_url and tab_id not in not_found_tabs:
            if any(re.search(pattern, page_url) for pattern in whitelist):
                print(f"Whitelisted: {page_url}")
            else:
                if tab_id in opened_tabs:
                    if opened_tabs[tab_id]["page_url"] != page_url:
                        opened_tabs[tab_id]["page_url"] = page_url
                        opened_tabs[tab_id]["visited"] = False
                else:
                    opened_tabs[tab_id] = {"page_url": page_url, "visited": False, "tab": None}

def close_browser_tab(url):
    try:
        tabs = driver.window_handles
        for tab in tabs:
            driver.switch_to.window(tab)
            if driver.current_url == url:
                driver.close()
                print(f"Closed NSFW tab: {url}")
                break
        driver.switch_to.window(tabs[0])  # Switch back to the first tab
    except Exception as e:
        print(f"Could not close tab for {url}: {e}")

def get_page_source(tab):
    driver.switch_to.window(tab)  # Switch to new tab
    time.sleep(0.5)  # Allow content to load
    page_url = driver.execute_script("return window.location.href;")
    html_content = driver.execute_script("return document.documentElement.outerHTML;")
    return page_url, html_content

def check_tab(tab):
    page_url, html_content = get_page_source(tab)
    print(f"Visiting {page_url}...")
    text = extract_text_from_html(html_content)
        # image_urls = get_image_urls(page_url)

    if is_nsfw_text(text):
        print(f"NSFW Content Detected in {page_url}")
        close_browser_tab(page_url)
        show_warning(page_url)