import os
import time
#Web Driver
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Parsing HTML
import requests

#Yahoo Financials
from yahoofinancials import YahooFinancials as yf

import pandas_datareader as pdr
import pandas_datareader.data as data

import timestring

# Excel operations
#import csv
import xlrd
import xlwt

# Date
import datetime
from datetime import datetime as dt, timedelta
from datetime import date

#List Files
from fractions import Fraction

import smtplib
import re

from bs4 import BeautifulSoup

from selenium.webdriver import ActionChains as ac

import time

def open_browser():
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    profile.set_preference("network.http.use-cache", False)
    profile.set_preference("browser.privatebrowsing.autostart", True)
    browser = webdriver.Firefox(profile)
    #browser.set_page_load_timeout(30)
    #browser.maximize_window()
    return browser

br=open_browser()
url="https://www.barchart.com/stocks/quotes/AVGO/interactive-chart"
br.get(url)
time.sleep(2)
try:
    #e=br.find_element_by_xpath("//*[@id="ic_guyoff6702"]")
    e=br.find_element_by_xpath("/html/body/div[9]/div[2]/div[3]/div/img")
    if e:
        e.click()
except Exception as e:
    print(str(e))

#try:
#    e=br.find_element_by_xpath("//*[@id="off7131"]")
#    if e:
#        e.click()
#except NoSuchElementException:
#    pass
    

#goto interactive chart
#e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[1]/div/div[2]/div[2]/div/ul/li[2]/ul/li[1]/a")
#e.click()

# change to line chart

#e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/interactive-chart/div[1]/div[2]/div[1]/div/div/div[1]/div[1]/div/div/a/img")
e = br.find_element_by_css_selector(".right-border-separator > div:nth-child(1) > div:nth-child(1) > a:nth-child(1) > img:nth-child(2)")
e.click()
e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/interactive-chart/div[1]/div[2]/div[1]/div/div/div[1]/div[1]/div/div/div/ng-transclude/div/ul/li[9]/div")
e.click()

# set max range
e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/interactive-chart/div[1]/div[2]/div[1]/div/div/div[2]/div[2]/ul/li[13]")
e.click()

# goto settings
e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/interactive-chart/div[1]/div[2]/div[1]/div/div/div[1]/button[3]/span")
e.click()

#goto adjustments
#e = br.find_element_by_xpath("/html/body/div[10]/div/div/form/div[2]/div[3]")
#e=br.find_element_by_xpath("/html/body/div[11]/div/div/form/div[2]/div[3]")
e = br.find_element_by_css_selector("div.bc-tabs__tab:nth-child(3)")
e.click()

#select earnings
#e = br.find_element_by_xpath("/html/body/div[11/div/div/form/div[5]/div[1]/ul/li[2]/div/label")
#e=br.find_element_by_css_selector(".row-events > ul:nth-child(2) > li:nth-child(2) > div:nth-child(1) > label:nth-child(2)")
e=br.find_element_by_css_selector(".row-events > ul:nth-child(2) > li:nth-child(2) > div:nth-child(1) > label:nth-child(2)")
e.click()

#apply
#e = br.find_element_by_xpath("/html/body/div[11]/div/div/div/button[2]")
e = br.find_element_by_css_selector("button.bc-button:nth-child(2)")
e.click()


soup = BeautifulSoup(br.page_source, 'html.parser')
pattern = re.compile(r'^E$')
entries = soup.findAll(text=pattern)
print(len(entries))


a = ac(br)
for e in entries:
    val = e.parent.parent.attrs['aria-label']
    attr = "g[aria-label=\'%s\'" %(val)
    we = br.find_element(By.CSS_SELECTOR, attr)
    h = a.move_to_element(we)
    h.perform()
    time.sleep(1)
    soup = BeautifulSoup(br.page_source, 'html.parser')
    e=soup.find("td", {"class":"field-value"})
    print("%s: %s" %(val,e.text))


