from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import os
import yaml

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
except Exception as e:
    raise RuntimeError(f"Error attaching session to browser: {e}")

file_path = os.path.join(os.path.dirname(__file__), "../config.yml")
try:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        whitelist = data.get("whitelisted_patterns", [])
        browsers = data.get("browser_processes", {})
except Exception as e:
    raise RuntimeError(f"Error loading config: {e}")