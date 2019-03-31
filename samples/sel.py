import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Firefox()
#driver.get("http://www.google.com")
#elem = driver.find_element_by_name("q")
driver.get("http://www.ratestar.in/home")
elem = driver.find_element_by_name("txtStock")
#driver.get("http://www.python.org")
#assert "Python" in driver.title
#elem = driver.find_element_by_name("q")

#stock='LT Foods Ltd.'
stock='ABB'
s=''
elem.clear()
for i in  range(len(stock)):
    s += stock[i]
    elem.send_keys(str(stock[i]))
    # Wait 100 msec
    time.sleep(100.0/1000.0)

#elem.send_keys(stock, Keys.ARROW_DOWN)
time.sleep(2)
elem.send_keys(Keys.RETURN)

time.sleep(20)
html_src=driver.page_source
print(html_src)

#try:
#    element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
#finally:
#    driver.close()

assert "No results found." not in driver.page_source
time.sleep(5)
driver.close()


