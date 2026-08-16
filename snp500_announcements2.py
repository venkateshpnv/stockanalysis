from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from internet import open_browser

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

#driver = webdriver.Chrome(options=options)
#driver.get('https://www.spglobal.com/spdji/en/media-center/news-announcements/#indexNews')
url = 'https://www.spglobal.com/spdji/en/media-center/news-announcements/#indexNews'
br = open_browser('headless')
br.get(url)

# Let the JS load fully
import time
time.sleep(5)

print(br.page_source[:1000])
br.quit()
