import subprocess

import psutil
import requests

from browser import browsers


def is_browser_running():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info["name"] in browsers.values():
            return proc.info["name"]
    return None


def restart_browser_with_devtools(browser):
    cmd = ["cmd", "/c", f"start {browser.split('.')[0]}", "--remote-debugging-port=9222",
           "--restore-last-session"] if browser in browsers.values() else None
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
            tabs = response.json()
            return [tab for tab in tabs if "url" in tab and tab["url"].startswith(("http://", "https://"))]
    except requests.RequestException as e:
        print(f"Error fetching tabs from DevTools: {e}")
    return []