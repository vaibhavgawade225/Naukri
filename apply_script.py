import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def run_bot():
    # Setup Chrome options for GitHub Actions (Headless mode is a must)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Access Secrets
    email = os.getenv('NAUKRI_EMAIL')
    password = os.getenv('NAUKRI_PASSWORD')

    # Your automation logic goes here
    driver.get("https://www.naukri.com/nlogin/login")
    print("Page Title:", driver.title)
    
    # Close
    driver.quit()

if __name__ == "__main__":
    run_bot()
