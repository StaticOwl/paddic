import time
import os
import requests
import platform
import subprocess
from bs4 import BeautifulSoup
from huggingface_hub import login
from transformers import pipeline

# #Read
# # login(token="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")
# #Write
# login(token="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")

pipe = pipeline("text-classification", model="michellejieli/NSFW_text_classifier")
os_type = platform.system()

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
    
def get_page_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()
    except requests.RequestException as e:
        print(f"Error fetching page content: {e}")
        return ""
    
def is_nsfw_text(text):
    if not text:
        return False
    result = pipe(text[:512])
    return any(res["label"] == "NSFW" and res["score"] > 0.8 for res in result)
    

    
if __name__ == "__main__":
    print(f"Monitoring browser activity on {os_type}...")
    previous_url = None
    while True:
        if os_type == "Darwin":
            url = get_active_browser_url_mac()
        else:
            url = None

        if url:
            print(f"Active browser URL: {url}")

