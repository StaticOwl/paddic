import time
import requests
import platform
import subprocess
from bs4 import BeautifulSoup
from huggingface_hub import login
from transformers import pipeline
import psutil
from plyer import notification
from PIL import Image
from io import BytesIO
import re
import pygetwindow as gw

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# #Read
# # login(token="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")
#Write
login(token="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")

text_pipe = pipeline("text-classification", model="eliasalbouzidi/distilbert-nsfw-text-classifier")
image_pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
os_type = platform.system()

BROWSER_PROCESSES = {
    "chrome" : "chrome.exe",
    "edge" : "msedge.exe",
    "brave" : "brave.exe"
}

WHITELISTED_PATTERNS = [
    r"google\.com",
    r"wikipedia\.org",
    r"github\.com",
    r"stackoverflow\.com",
    r"youtube\.com",
    r"chatgpt\.com"
]

def is_browser_running():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info["name"] in BROWSER_PROCESSES.values():
            return proc.info["name"]
    return None

def restart_browser_with_devtools(browser):
    cmd = ["cmd", "/c", f"start {browser.split('.')[0]}", "--remote-debugging-port=9222", "--restore-last-session"] if browser in BROWSER_PROCESSES.values() else None
    if not cmd:
        return
    else:
        print(cmd)
    print(f"Restarting {browser} with remote debugging enabled...")
    subprocess.run(["taskkill", "/IM", browser, "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def is_debugging_active():
    try:
        response = requests.get("http://localhost:9222/json", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_tabs_from_devtools():
    try:
        response = requests.get("http://localhost:9222/json", timeout=2)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        print(f"Error fetching tabs from DevTools: {e}")
    return []

def update_tab_urls(opened_tabs, not_found_tabs):
    devtools_tabs = get_tabs_from_devtools()
    for tab in devtools_tabs:
        tab_id = tab.get("id")
        page_url = tab.get("url")

        if tab_id and page_url and tab_id not in not_found_tabs:
            if any(re.search(pattern, page_url) for pattern in WHITELISTED_PATTERNS):
                print(f"Whitelisted: {page_url}")
            else:
                if tab_id in opened_tabs:
                    if opened_tabs[tab_id]["page_url"] != page_url:
                        opened_tabs[tab_id]["page_url"] = page_url
                        opened_tabs[tab_id]["visited"] = False
                else:
                    opened_tabs[tab_id] = {"page_url": page_url, "visited": False, "tab": None}


def attach_to_browser():
    options = webdriver.ChromeOptions()
    options.debugger_address = "localhost:9222"
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--window-size=1920,1080")
    service = Service()

    try:
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error attaching to browser: {e}")
        return None

def get_page_source(driver, tab):
    driver.switch_to.window(tab)  # Switch to new tab
    time.sleep(0.5)  # Allow content to load
    page_url = driver.execute_script("return window.location.href;")
    html_content = driver.execute_script("return document.documentElement.outerHTML;")
    return page_url, html_content

def get_active_browser_url_mac():
    try:
        script = """
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
        end tell
        if frontApp is "Google Chrome" then
            tell application "Google Chrome" to return URL of active tab of front window
        else if frontApp is "Brave Browser" then
            tell application "Brave Browser" to return URL of active tab of front window
        else if frontApp is "Microsoft Edge" then
            tell application "Microsoft Edge" to return URL of active tab of front window
        else if frontApp is "Safari" then
            tell application "Safari" to return URL of front document
        else
            return "Unknown"
        end if
        """
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        url = result.stdout.strip()
        print(result.stdout.strip())
        if url.startswith("http"):
            return url
        return None
    except Exception as e:
        print(f"Error getting active browser URL on macOS: {e}")
        return None
    
def get_active_browser_url_windows():
    try:
        response = requests.get("http://localhost:9222/json", timeout=2)
        tabs = response.json()
        urls = [tab["url"] for tab in tabs if "url" in tab and tab["url"].startswith("http")]

        return urls

    except requests.RequestException as e:
        print(f"Error fetching active tab URL: {e}")

    return None

def extract_text_from_html(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text().strip().replace("\n", " ")

def get_image_urls(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        img_tags = soup.find_all("img")

        image_urls = set()

        for img in img_tags:
            # Extract from 'src'
            src = img.get("src")
            if src:
                image_urls.add(requests.compat.urljoin(url, src))

            # Extract from 'srcset' (handle multiple URLs)
            srcset = img.get("srcset")
            if srcset:
                for img_url in srcset.split(","):
                    clean_url = img_url.strip().split(" ")[0]  # Remove resolution descriptors
                    image_urls.add(requests.compat.urljoin(url, clean_url))

            # Extract from 'data-sprite'
            sprite = img.get("data-sprite")
            if sprite:
                image_urls.add(requests.compat.urljoin(url, sprite))

        return list(image_urls)

    except requests.RequestException as e:
        print(f"Error fetching image URLs: {e}")
        return []

    
def is_nsfw_text(text):
    if not text:
        return False

    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    chunks = [text[i: i+512] for i in range(0, len(text), 512)]

    for chunk in chunks:
        result = text_pipe(chunk)
        if any(res["label"] == "nsfw" and res["score"] > 0.7 for res in result):  # Lower threshold slightly
            return True

    return False

def is_nsfw_image(image_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    print("Image URL:", image_url)
    try:
        response = requests.get(image_url, headers=headers, timeout=5)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        
        result = image_pipe(img)
        print("Image:" , result)
        return any(res["label"].lower() in ["nsfw", "porn", "explicit"] and res["score"] > 0.8 for res in result)

    except requests.RequestException as e:
        print(f"Error fetching image: {e}")
        return False
    except Exception as e:
        print(f"Error processing image: {e}")
        return False

def show_warning(page_url):
    notification.notify(
        title="Warning!",
        message=f"{page_url} contains explicit content and has been blocked.",
        timeout=5
    )

def close_browser_tab(driver, url):
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

def check_tab(driver, tab):
    page_url, html_content = get_page_source(driver, tab)
    print(f"Visiting {page_url}...")
    text = extract_text_from_html(html_content)
        # image_urls = get_image_urls(page_url)

    if is_nsfw_text(text):
        print(f"NSFW Content Detected in {page_url}")
        close_browser_tab(driver, page_url)
        show_warning(page_url)

def is_tab_open(driver, tab_handle):
    return tab_handle in driver.window_handles

    
if __name__ == "__main__":
    browser_process = is_browser_running()
    if browser_process and not is_debugging_active():
        restart_browser_with_devtools(browser_process)

    if is_debugging_active():
        print(f"Monitoring browser activity on {os_type}...")

        driver = attach_to_browser()
        opened_tabs = {}
        not_found_tabs = set()

        if not driver:
            print("Failed to attach to browser. Make sure the browser is running in debugging mode.")
            exit()
        for tab in opened_tabs:
            check_tab(driver, tab)

        while True:
            update_tab_urls(opened_tabs, not_found_tabs)
            print(opened_tabs)
            print(not_found_tabs)

            for tab_id, tab_info in list(opened_tabs.items()):
                if not tab_info["visited"]:
                    if tab_info["tab"] is None:

                        print(f"Opening {tab_info['page_url']}...")
                        for handle in driver.window_handles:
                            driver.switch_to.window(handle)
                            if driver.current_url == tab_info["page_url"]:
                                tab_info["tab"] = handle
                                break
                        if tab_info["tab"] is None:
                            print("Tab not found.")
                            not_found_tabs.add(tab_id)
                            continue

                    if tab_info["tab"]:
                        print(f"Checking {tab_info['page_url']}...")
                        check_tab(driver, tab_info["tab"])
                        tab_info["visited"] = True
            # print("Checking for new tabs...")
            # new_tabs = set(driver.window_handles) - opened_tabs
            # if new_tabs:
            #     if current_tab:
            #         opened_tabs.add(current_tab)
            #     current_tab = max(new_tabs, key=lambda x: int(x, 16))
            #     print("Switching to new tab...")
            #
            # elif current_tab and not is_tab_open(driver, current_tab):
            #     if opened_tabs:
            #         current_tab = max(opened_tabs, key=lambda x: int(x, 16))
            #         print("Switching to last opened tab...")
            #
            # elif not current_tab and opened_tabs and not new_tabs:
            #     current_tab = max(opened_tabs, key=lambda x: int(x, 16))
            #
            # check_tab(driver, current_tab)
            for tab_id in not_found_tabs:
                if tab_id in opened_tabs:
                    del opened_tabs[tab_id]
            print(opened_tabs)
            time.sleep(2)
