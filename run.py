import time
import requests
import platform
import subprocess
from bs4 import BeautifulSoup
from huggingface_hub import login
from transformers import pipeline
import psutil
import notification
from PIL import Image
from io import BytesIO

# #Read
# # login(token="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")
#Write
login(token="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")

text_pipe = pipeline("text-classification", model="eliasalbouzidi/distilbert-nsfw-text-classifier")
image_pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
os_type = platform.system()

previous_urls = set()

BROWSER_PROCESSES = {
    "chrome" : "chrome.exe",
    "edge" : "msedge.exe",
    "brave" : "brave.exe"
}

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

def get_page_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text().strip().replace("\n", " ")
    except requests.RequestException as e:
        print(f"Error fetching page content: {e}")
        return ""

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
    print(text)
    # print(text[:512])
    result = text_pipe(text[:512])
    print("Text:" , result)
    return any(res["label"] == "NSFW" and res["score"] > 0.95 for res in result)

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

def show_warning():
    notification.notify(
        title="Warning!",
        message="This website contains explicit content and has been blocked.",
        timeout=5
    )

def close_browser_tab_windows():
    try:
        subprocess.run(["powershell", "-Command", "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys('^w')"], check=True)
    except Exception as e:
        print(f"Could not close browser tab on Windows: {e}")

    
if __name__ == "__main__":
    print(f"Monitoring browser activity on {os_type}...")

    while True:
        match os_type:
            case "Darwin":
                url = get_active_browser_url_mac()
            case "Windows":
                browser_process = is_browser_running()
                if browser_process and not is_debugging_active():
                    restart_browser_with_devtools(browser_process)

                open_urls = get_active_browser_url_windows() if is_debugging_active() else None

                if not previous_urls:
                    urls_to_check = open_urls
                else:
                    urls_to_check = [url for url in open_urls if url not in previous_urls]

                for url in urls_to_check:
                    print(f"Checking URL: {url}")
                    text = get_page_text(url)
                    nsfw_text_detected = is_nsfw_text(text)
                    # nsfw_image_detected = any(is_nsfw_image(img_url) for img_url in get_image_urls(url))

                    if nsfw_text_detected:
                        print(f"NSFW content detected on {url}")
                        # show_warning()
                        # close_browser_tab_windows()

                previous_urls.update(open_urls)
                time.sleep(5)

            case _:
                print("Unsupported OS")
                break