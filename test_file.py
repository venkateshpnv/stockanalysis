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
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

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
    #profile.set_preference("browser.cache.disk.enable", False)
    #profile.set_preference("browser.cache.memory.enable", False)
    #profile.set_preference("browser.cache.offline.enable", False)
    #profile.set_preference("network.http.use-cache", False)
    #profile.set_preference("browser.privatebrowsing.autostart", True)
   
    #profile.set_preference("browser.download.manager.showWhenStarting", False)
    #profile.set_preference("browser.download.folderList", 2)
    #profile.set_preference("browser.download.dir", "/tmp")
    #profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")
    
    
    profile.set_preference("browser.download.dir","/tmp/")
    profile.set_preference("browser.download.defaultFolder","/tmp/")
    profile.set_preference("browser.download.folderList",2)
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/plain,text/x-csv,text/csv,application/vnd.ms-excel,application/csv,application/x-csv,text/csv,text/comma-separated-values,text/x-comma-separated-values,text/tab-separated-values,application/pdf,application/octet-stream")
    profile.set_preference("browser.download.manager.showWhenStarting",False)
    profile.set_preference("browser.helperApps.neverAsk.openFile","text/plain,text/x-csv,text/csv,application/vnd.ms-excel,application/csv,application/x-csv,text/csv,text/comma-separated-values,text/x-comma-separated-values,text/tab-separated-values,application/pdf")
    profile.set_preference("browser.helperApps.alwaysAsk.force", False)
    profile.set_preference("browser.download.manager.useWindow", False)
    profile.set_preference("browser.download.manager.focusWhenStarting", False)
    profile.set_preference("browser.helperApps.neverAsk.openFile", "")
    profile.set_preference("browser.download.manager.alertOnEXEOpen", False)
    profile.set_preference("browser.download.manager.showAlertOnComplete", False)
    profile.set_preference("browser.download.manager.closeWhenDone", True)
    profile.set_preference("pdfjs.disabled", True)
    
    caps = DesiredCapabilities.FIREFOX
    browser = webdriver.Firefox(firefox_profile=profile, capabilities=caps)
    #browser = webdriver.Firefox(profile)
    
    #browser.set_page_load_timeout(30)
    #browser.maximize_window()
    
    
    return browser

def scroll(br, direction):
    e=br.find_element_by_tag_name('html')
    for i in range(5):
        e.send_keys(direction)


def main():
    #br = open_browser()
    #br.maximize_window()
    nasdaq_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
    wb=requests.get(nasdaq_url)
    f=open("/tmp/nasdaq.csv","wb")
    f.write(wb.content)
    f.close()

    nyse_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download"
    wb=requests.get(nyse_url)
    f=open("/tmp/nyse.csv","wb")
    f.write(wb.content)
    f.close()

    amex_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download"
    wb=requests.get(amex_url)
    f=open("/tmp/amex.csv","wb")
    f.write(wb.content)
    f.close()


main()
