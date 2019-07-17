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
from selenium.webdriver import ActionChains as ac

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gc

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

import pprint

import threading

import excel
import conf
from datastructures import *
import parse_html
import DB
from common import *

def open_browser():
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    profile.set_preference("network.http.use-cache", False)
    profile.set_preference("browser.privatebrowsing.autostart", True)
    profile.set_preference("dom.webnotifications.enabled", False)
    browser = webdriver.Firefox(profile)
    #browser.set_page_load_timeout(30)
    #browser.maximize_window()
    return browser

def close_browser(br):
    #br.close()
    br.delete_all_cookies()
    br.quit()

def send_email(message):
    # creates SMTP session 
    s = smtplib.SMTP('smtp.gmail.com', 587) 
      
    # start TLS for security
    s.ehlo()
    s.starttls() 
      
    # Authentication 
    s.login("askpvenkatesh@gmail.com", "tasche#gm") 
      
    # message to be sent 
    message = "Hello World."
      
    # sending the mail 
    s.sendmail("askpvenkatesh@gmail.com", "askpvenkatesh@gmail.com", message) 
      
    # terminating the session 
    s.quit() 

def send_email2(user, pwd, recipient, subject, body):

    FROM = user
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    #message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    #""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = user
    message['To'] = recipient
    message.attach(MIMEText(body, 'html'))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(user, pwd)
    server.sendmail(FROM, TO, message.as_string())
    #server.sendmail(FROM, TO, message)
    server.close()
    print('successfully sent the mail')

def price_change(country, sym, name, num_days, data_type):
    change = 0
    if data_type == 'HOT':
        end = dt.now()
        start = end - timedelta(days=num_days)
        try:
            #print("Symbol: %s, Name: %s" %(sym, name))
            read = pdr.DataReader(sym, 'yahoo', start, end)
        except pdr._utils.RemoteDataError:
            PRINT_ERR("Unable to get data for %s"%(sym))
            return None
        except KeyError:
            PRINT_ERR("Unable to get data for %s"%(sym))
            return None
 
        #st_price = None
        #start = end - timedelta(days=num_days)
        ##end = dt.now()
        #
        ## Get data's first row date
        #data_start_date = read.index.to_pydatetime()[0]

        ## Some times, the stock has been started trading recently.
        ## You don't have yearly or even longer historical data
        ## Assume the start point as the earliest start date
        #if start.date() < data_start_date.date():
        #    start = data_start_date

        #num_days = (end-start).days

#        for index, row in read.iterrows():
#            if index.date() == start.date():
#                st_price = row['Adj Close']
#                break
#
#        if not st_price:
#            PRINT_ERR("Unable to get start price for sym: %s, name: %s, num_days: %d" %(sym, name, num_days))
#            return 0

        en_price = read.iat[-1, read.columns.get_loc('Adj Close')]
        st_price = read.iat[0, read.columns.get_loc('Adj Close')]
        change = en_price/st_price - 1
    elif data_type == 'COLD':
        db = DB.open_db('Stocks')
        if country == 'US':
            doc = db.US_Stocks.find({"bscs.symbol":sym})
        elif country == 'India':
            docs = db.Indian_Stocks.find({"bscs.symbol":sym})
        else:
            return 0
        if num_days == 365:
            val = doc[0]['price_change']['year']
            if val:
                change = float(val)
        elif num_days == 90:
            val = doc[0]['price_change']['quarter']
            if val:
                change = float(val)
        elif num_days == 30:
            val = doc[0]['price_change']['month']
            if val:
                change = float(val)
        elif num_days == 7:
            val = doc[0]['price_change']['week']
            if val:
                change = float(val)
        elif num_days == 2 or num_days == 3:
            val = doc[0]['price_change']['day']
            if val:
                change = float(val)

    return change

def check_price_change(country, sym, stock, name, change, req_change, count, sheet, sheet_type):
    if change >= req_change:
        #print("sym: %s, name: %s, change: %d percent" %(sym, name, change*100))
        count += 1 
        excel.write_to_price_change_excel(count, sheet, stock, sheet_type)

    elif change < -(req_change):
        #print("sym: %s, name: %s, change: -%d percent" %(sym, name, change*100))
        count += 1 
        excel.write_to_price_change_excel(count, sheet, stock, sheet_type)

    return count


def price_suprise(country, collection, stock, sym, name, change_percent, xl, data_type, criteria, db_type):
   #st_price = read.iat[0, read.columns.get_loc('Close')]
    #en_price = read.iat[-1, read.columns.get_loc('Close')]
   
    if data_type == 'HOT':
        DB.update_field(collection, sym, "price_change.date", str(dt.now().date()))

    if criteria == ALL or criteria & YEAR:
        change = price_change(country, sym, name, 365, data_type)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.year", change)
            conf.PR_YR_COUNT = check_price_change(country, sym, stock, name, change, 0.40, conf.PR_YR_COUNT, xl.get_sheet(0), 'YEAR')
    
    if criteria == ALL or criteria & QUARTER:
        change = price_change(country, sym, name, 90, data_type)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.quarter", change)
            conf.PR_QR_COUNT = check_price_change(country, sym, stock, name, change, 0.30, conf.PR_QR_COUNT, xl.get_sheet(1), 'QUARTER')
    
    if criteria == ALL or criteria & MONTH:
        change = price_change(country, sym, name, 30, data_type)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.month", change)
            conf.PR_MON_COUNT = check_price_change(country, sym, stock, name, change, 0.20, conf.PR_MON_COUNT, xl.get_sheet(2), 'MONTH')
    
    if criteria == ALL or criteria & WEEK:
        change = price_change(country, sym, name, 7, data_type)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.week", change)
            conf.PR_WEEK_COUNT = check_price_change(country, sym, stock, name, change, 0.10, conf.PR_WEEK_COUNT, xl.get_sheet(3), 'WEEK')

    if criteria == ALL or criteria & DAY:
        change = price_change(country, sym, name, 2, data_type)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.day", change)
            conf.PR_DAY_COUNT = check_price_change(country, sym, stock, name, change, 0.10, conf.PR_DAY_COUNT, xl.get_sheet(4), 'DAY')

def price_surprises(country, change_percent, criteria, data_type, db_type):
    print("Criteria: %r" %(criteria))
    xl = xlwt.Workbook()

    yr_sheet = xl.add_sheet("365 days change")
    qr_sheet = xl.add_sheet("90 days change")
    mon_sheet = xl.add_sheet("30 days change")
    week_sheet = xl.add_sheet("7 days change")
    day_sheet = xl.add_sheet("one day change")

    excel.add_price_surprise_header(yr_sheet, 'YEAR')
    excel.add_price_surprise_header(qr_sheet, 'QUARTER')
    excel.add_price_surprise_header(mon_sheet, 'MONTH')
    excel.add_price_surprise_header(week_sheet, 'WEEK')
    excel.add_price_surprise_header(day_sheet, 'DAY')

    db = DB.open_db('Stocks')
    if country == 'US':
        col = db['US_Stocks']
        #for doc in col.find({"bscs.industry":"Accident &Health Insurance"}):
        #for doc in col.find({}):
        docs = col.find({}).sort([["sno",1]])
        print("Count: %r" %(docs.count()))
        i=0
        len_skip= dcf_skip = price_skip = trading_skip = vol_skip = 0
        for doc in docs:
            sno = doc['sno']
            if sno > 150:
            #if sno > 0:
                doc['id'] = doc.pop('_id')
                stock = DB.dbObject(**doc)
                sym = doc['bscs']['symbol']
                name = doc['bscs']['name']
                #print("%r : "%(i), end = '')

                list=doc['num']
                if len(list) == 0:
                    len_skip+=1
                    continue
                if "dcf_years" not in list.keys():
                    dcf_skip+=1
                    continue
                if stock.bscs.price < 1:
                    price_skip+=1
                    continue
                if stock.bscs.trading != 'YES':
                    trading_skip+=1
                    continue
                if stock.bscs.volume < 40000:
                    vol_skip+=1
                    continue
                i+=1
                print("%d: %d: %s: %s" %(i, sno, sym, name))
                price_suprise(country, col, stock, sym, name, change_percent, xl, data_type, criteria, db_type)
        print("len_skip: %r, dcf_skip = %d, price_skip = %d, trading_skip = %d, vol_skip = %d" %(len_skip, dcf_skip, price_skip, trading_skip, vol_skip))
    elif country == 'India':
        col = db['India_Stocks']
        for doc in col.find({}):
            if i > -1:
                doc['id'] = doc.pop('_id')
                stock = dbObject(**doc)
                sym = doc['bscs']['symbol']
                name = doc['bscs']['name']
                sym = sym + '.BO'
                price_suprise(country, col, stock, sym, name, change_percent, xl, data_type, criteria, db_type)
            i += 1

    #now = datetime.datetime.now().date()
    now = datetime.datetime.now()
    excel_file = "US_Stocks/DCF_Calc/price_surprises_%s.xls" % (str(now))
    #xl.save("US_Stocks/DCF_Calc/price_surprises.xls")
    xl.save(excel_file)


def get_price_volume(stk, country):
    #data = pdr.get_data_yahoo(symbols=stk.bscs.symbol, start=dt(2019,4,15), end=dt(2019,4,18))
    #stk.bscs.price  = round(float(data.iat[-1, data.columns.get_loc('Adj Close')]), 2)
    #vol = data[['Volume']]
    #sum = 0        
    #for v in vol.values.tolist():
    #    sum += v[0]
    #stk.bscs.volume = sum / len(vol.values.tolist())
    
    ##data.get_quote_yahoo(stocklist).to_csv('test.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)
    try:
        if country == 'India':
            d = data.get_quote_yahoo(stk.bscs.symbol+'.BO')
        elif country == 'US':
            d = data.get_quote_yahoo(stk.bscs.symbol)
        else:
            PRINT_ERR("Unknown Country Name")
            return None
    except KeyError:
        PRINT_ERR("Unable to get price and volume for %s"%(stk.bscs.symbol))
        return None
    except pdr._utils.RemoteDataError:
        PRINT_ERR("Unable to get data for %s: %s"%(stk.bscs.name, stk.bscs.symbol))
        return None
    try:
        # Add moving average etc. Refer /tmp/test.csv for details
        stk.bscs.volume = (d.averageDailyVolume3Month.to_list()[0])
        #stk.bscs.volume = d.regularMarketVolume.to_list()[0]
        stk.bscs.mcap   = float(d.marketCap.to_list()[0])/1000000
        stk.bscs.price  = (d.price.to_list()[0])
        stk.bscs.outstanding_shares = d.sharesOutstanding.to_list()[0]
    except AttributeError as e:
        PRINT_ERR(str(e))
        PRINT_ERR("Couldn't get a particular field for %s" %(stk.bscs.symbol))
    return stk

def get_price_growth(country, stk, years, data_type):
    if stk.bscs.price_years != 5 and stk.bscs.price_years != 10 and stk.bscs.price_years != 0:
        yrs = int(stk.bscs.price_years)
    else:
        yrs = years

    if data_type == 'HOT':
        end = dt.today()
        st = dt(end.year-years, end.month, end.day)
        print("start: %s, end: %s" %(st.date(), end.date()))
        try:
            data = pdr.DataReader(stk.bscs.symbol, 'yahoo', st, end)
        except pdr._utils.RemoteDataError:
            PRINT_ERR("Unable to get data for %s: %s"%(stk.bscs.name, stk.bscs.symbol))
            stk.bscs.hist_price_5 = 1
            stk.bscs.hist_price_10 = 1
            return 0

        st_price = data.iat[0, data.columns.get_loc('Close')]
        en_price = data.iat[-1, data.columns.get_loc('Close')]
        yrs = end.year - int(str(list(data.index)[0]).split('-')[0])
        print("yrs: %d, %s" %(yrs, str(list(data.index)[0]).split('-')[0]))
        del data
        if years <= 5:
            stk.bscs.hist_price_5 = st_price
        else:
            end = dt.today()
            st = dt(end.year-5, end.month, end.day)
            data = pdr.DataReader(stk.bscs.symbol, 'yahoo', st, end)
            stk.bscs.hist_price_5 = data.iat[0, data.columns.get_loc('Close')]
            del data
 
        if years > 5 and years <= 10:
            stk.bscs.hist_price_10 = st_price
        else:
            end = dt.today()
            st = dt(end.year-10, end.month, end.day)
            data = pdr.DataReader(stk.bscs.symbol, 'yahoo', st, end)
            stk.bscs.hist_price_10 = data.iat[0, data.columns.get_loc('Close')]
            del data

        db = DB.open_db('Stocks')
        if country  == 'US':
            collection = db['US_Stocks']
        elif country == 'India':
            collection = db['India_Stocks']
        else:
            raise exception("Unknown Country Name %s" %(country))

        DB.update_field(collection, stk.bscs.symbol, "bscs.hist_price_5", stk.bscs.hist_price_5)
        DB.update_field(collection, stk.bscs.symbol, "bscs.hist_price_10", stk.bscs.hist_price_10)
        DB.update_field(collection, stk.bscs.symbol, "bscs.price", round(en_price,2))
        DB.update_field(collection, stk.bscs.symbol, "bscs.price_years", yrs)
 
    if yrs < 1:
        yrs = 1
    if years == 10:
        st_price = stk.bscs.hist_price_10
    else:
        st_price = stk.bscs.hist_price_5

    en_price = stk.bscs.price
    #    st_price = round(float(st_price.real),2)
    #if isinstance(en_price, complex):
    #    en_price = rount(float(en_price.real),2)
    years = yrs
    try:
        growth = round(((en_price/st_price)**(1/years)-1), 2)
    except ZeroDivisionError:
        growth = 0
    PRINT("years: %d, growth: %r" %(years, growth))
    return growth

# Get stock split information
def get_stock_split_info_yahoo(country, stk):
    if country == 'India':
        sym = stk.bscs.symbol + '.BO'
    elif country != 'US':
        PRINT_ERR("Unknown Country")
        return
    #get split info from Yahoo Finance
    data = yf(sym).get_key_statistics_data()
    stk.bscs.split_factor = float(Fraction(data[sym]['lastSplitFactor']))
    d = data[sym]['lastSplitDate']
    stk.bscs.split_date = d
    stk.bscs.split_year = datetime.datetime.strptime(d, '%Y-%m-%d').year 

def get_LTP(country, sym):
    sym1 = sym
    if country == 'India':
        sym = sym + '.BO'
    elif country != 'US':
        PRINT_ERR("Unknown Country")
        return 0
    price = yf(sym).get_current_price()
    if not price and '.' in sym:
        sym = sym.replace('.', '-')
        price = yf(sym).get_current_price()
    if not price:
        PRINT_ERR("Unable to get latest price for %s" %(sym))
        PRINT_ERR("Updating stock to not trading")
        db = DB.open_db('Stocks')
        if country == 'US':
            col = db.US_Stocks
        elif country == 'India':
            col = db.India_Stocks
        else:
            return 0
        DB.update_field(col, sym1, "bscs.trading", "NO")
        return 0
    return price

def get_page(url, html_file):
    html=requests.get(url)
    if html.status_code == 200:
        write_to_file(html.text, html_file)
    else:
        PRINT_ERR("Couldnt get page : %s" %(url))

def get_webpage(url):
    return requests.get(url).text

def browse_US_stock_page(stock, url):
    driver = webdriver.Firefox()
    driver.set_page_load_timeout(30)
    driver.get(url)
    old_url = driver.current_url
    driver.maximize_window()

    time.sleep(5)
    elem = driver.find_element_by_class_name("panclose5084")
    if elem:
        elem.click()
    return
    elem = driver.find_element_by_class_name("bc-button white-button small settings-button")
    elem.click()
    time.sleep(20)
    driver.close()

        # attr=driver.find_element_by_name('txtStock').get_attribute('innerHTML')
        # attr=elem.get_attribute('innerHTML')
    # elem.send_keys(stock, Keys.ARROW_DOWN)
    # time.sleep(2)
    # elem.send_keys(Keys.RETURN)

"""
    # time.sleep(20)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (By.ID, 'lblCompany')))
    except TimeoutException:
        PRINT("Unable to parse %r" % (stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
        return
    # PRINT_DBG(str(html_src))

    if driver.current_url == old_url:
        PRINT("Unable to parse %r" % (stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        # PRINT_DBG("Found stock %r" %(stock))
        html_src = driver.page_source
        html_file = "html_pages/%s.html" % (stock_name)
        f = open(html_file, "w")
        f.write(html_src)
        f.close()
"""
    #    try:
    #        element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
    #        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, 'IdOfMyElement')))
    #        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    #        html_file = "html_pages/%s.html" %(stock)
    #        f = open(html_file, "w")
    #        f.write(html_src)
    #        f.close()
    #    finally:
    #        PRINT_DBG("Unable to parse %r" %(stock))
    #        f = open("unparsed_stocks.txt", "a")
    #        f.write(stock)
    #        f.write("\n")
    #        f.close()

    #driver.close()

    # try:
    #    element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
    # finally:
    #    driver.close()

    # assert "No results found." not in driver.page_source
    # time.sleep(5)

def get_US_earnings_estimates(symbol, name):
    driver = webdriver.Firefox()
    driver.set_page_load_timeout(30)

    url = "https://www.barchart.com/stocks/quotes/%s/earnings-estimates" %(symbol)
    
    driver.get(url)
    old_url = driver.current_url
    driver.maximize_window()

    html_file = "%s/%s_earnings_estimates.html" %(path, symbol)
    get_page(url, html_file)
    return 

def update_DB_US_earnings_estimates(stk, earnings, fiftytwoweek_high, fiftytwoweek_low):
    db = DB.open_db('Stocks')
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "bscs.fiftytwoweek_high", fiftytwoweek_high)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "bscs.fiftytwoweek_low", fiftytwoweek_low)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.date", earnings.date)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.high_target", earnings.high_target)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.mean_target", earnings.mean_target)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.low_target", earnings.low_target)

    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.hist.quarters", earnings.hist.quarters)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.hist.reported", earnings.hist.reported)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.hist.estimate", earnings.hist.estimate)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.hist.difference", earnings.hist.difference)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.hist.surprise", earnings.hist.surprise)

    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.quarters", earnings.est.quarters)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.years", earnings.est.years)

    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.q_avg_est", earnings.est.q_avg_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.q_num_est", earnings.est.q_num_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.q_high_est", earnings.est.q_high_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.q_low_est", earnings.est.q_low_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.q_prior_yr", earnings.est.q_prior_yr)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.q_gr_rate", earnings.est.q_gr_rate)

    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.y_avg_est", earnings.est.y_avg_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.y_num_est", earnings.est.y_num_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.y_high_est", earnings.est.y_high_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.y_low_est", earnings.est.y_low_est)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.y_prior_yr", earnings.est.y_prior_yr)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "quart_fig.Earning_Estimates.est.y_gr_rate", earnings.est.y_gr_rate)

def click_sym(symbol, elem):
    print(len(elem))
    
def populate_US_earnings_estimates(stk):
    earnings = Earnings()

    url = "https://www.barchart.com/stocks/quotes/%s/earnings-estimates" %(stk.bscs.symbol)
    br = open_browser()
    try:
        br.get(url)
    except Exception:
        print("%s: %s webpage loading timeout, trying again" %(stk.bscs.symbol, stk.bscs.name))
        close_browser(br)
        time.sleep(5)
        br = open_browser()
        br.get(url)

    #time.sleep(5)
    #ad popup
    try:
        e = br.find_element_by_xpath("/html/body/div[8]/div[2]/div[1]")
        e.click()
    except Exception:
        PRINT("No popup")

    try:
        page = br.page_source
    except Exception as e:
        print("%s: %s page source exception trying again, err: %s" %(stk.bscs.symbol, stk.bscs.name, str(e)))
        time.sleep(5)
        br.get(url)
        page = br.page_source

    soup = parse_html.get_soup(page)

    if soup.find("title").text.lstrip().rstrip() == 'Page not found':
        PRINT_ERR("%s:%s Invalid page, skipping" %(stk.bscs.symbol, stk.bscs.name))
        update_DB_US_earnings_estimates(stk, earnings, stk.bscs.price, stk.bscs.price)
        close_browser(br)
        return

    msg = ' Earnings are not available for %s.  ' %(stk.bscs.symbol)
    pattern = re.compile(r'%s'%msg)
    div = soup.find(text=pattern)
    if div:
        PRINT_ERR("%s:%s does not have earnings estimates, skipping" %(stk.bscs.symbol, stk.bscs.name))
        update_DB_US_earnings_estimates(stk, earnings, stk.bscs.price, stk.bscs.price)
        close_browser(br)
        return
    
    l=soup.find(text=re.compile('^HIGH TARGET '))
    earnings.high_target = str_to_float(l.parent.text.split(' ')[-1])
    l=soup.find(text=re.compile('^LOW TARGET '))
    earnings.low_target = str_to_float(l.parent.text.split(' ')[-1])
    l=soup.find(text=re.compile('^MEAN TARGET '))
    earnings.mean_target = str_to_float(l.parent.text.split(' ')[-1])

    l=soup.find(text=re.compile('^52 WK High '))
    fiftytwoweek_high = str_to_float(l.parent.text.split(' ')[-1])
    l=soup.find(text=re.compile('^52 WK Low '))
    fiftytwoweek_low = str_to_float(l.parent.text.split(' ')[-1])


    l = soup.find("span", {"class": "last-change ng-binding"})
    DB.update_field(DB.open_db('Stocks').US_Stocks, stk.bscs.symbol, "bscs.price", str_to_float(l.text))

    l=soup.find_all(text=re.compile('^Qtr Ending'))
    for entry in l:
        earnings.hist.quarters.append(entry.parent.parent.text.split(' ')[3])

    l=soup.find(text=re.compile('^Reported'))
    entries=l.parent.parent.parent.text.split(' ')
    for entry in entries[5:-1]:
        if entry != '':
            earnings.hist.reported.append(str_to_float(entry))

    l=soup.find(text=re.compile('^Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    for entry in entries[5:-1]:
        if entry != '':
            earnings.hist.estimate.append(str_to_float(entry))

    for i in range(len(earnings.hist.estimate)):
        est = earnings.hist.estimate[i]
        rep = earnings.hist.reported[i]
        earnings.hist.difference.append(round(rep-est,3))
        try:
            earnings.hist.surprise.append(round(((rep - est)/ est), 4))
        except ZeroDivisionError:
            earnings.hist.surprise.append(0)

    l=soup.find(text=re.compile('^Current Qtr'))
    earnings.est.quarters.append(l.parent.parent.text.split(' ')[-2])
    l=soup.find(text=re.compile('^Next Qtr'))
    earnings.est.quarters.append(l.parent.parent.text.split(' ')[-2])
    l=soup.find_all(text=re.compile('^Fiscal Yr'))
    earnings.est.years.append(l[0].parent.parent.text.split(' ')[-2])
    earnings.est.years.append(l[1].parent.parent.text.split(' ')[-2])

    l=soup.find(text=re.compile('^Average Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_avg_est.append(str_to_float(entry))
            else:
                earnings.est.y_avg_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Number of Estimates'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_num_est.append(str_to_float(entry))
            else:
                earnings.est.y_num_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^High Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_high_est.append(str_to_float(entry))
            else:
                earnings.est.y_high_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Low Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_low_est.append(str_to_float(entry))
            else:
                earnings.est.y_low_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Prior Year'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_prior_yr.append(str_to_float(entry))
            else:
                earnings.est.y_prior_yr.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Growth Rate Est'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[14:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_gr_rate.append(round(str_to_float(entry)/100,4))
            else:
                earnings.est.y_gr_rate.append(round(str_to_float(entry)/100,4))
            count += 1

    earnings.date=str(dt.now().date())
    earnings.hist.quarters.reverse()
    earnings.hist.reported.reverse()
    earnings.hist.estimate.reverse()
    earnings.hist.difference.reverse()
    earnings.hist.surprise.reverse()

    #elem = br.find_element_by_name("search")
    #elem.send_keys("FIVE")
    ##time.sleep(10)
    ##page = br.page_source
    ##f=open("/tmp/five.html", "w")
    ##f.write(soup.prettify())
    ##f.close()
    #opts = WebDriverWait(br, 10).until(EC.presence_of_element_located(
    #        (By.CLASS_NAME, 'quick-search')))
    ##elem = br.find_element_by_class_name("quick-search")

	#br.find_element_by_name("search").clear()
	#br.find_element_by_name("search").send_keys("Five Below")
	#br.find_element_by_name("search").send_keys(Keys.ARROW_DOWN)
	#br.find_element_by_name("search").send_keys(Keys.RETURN)

    #click_sym(stk.bscs.symbol, elem)
    #print("Opts: %r : %r" %(len(opts.text), opts.text))

    #return
 
    #try:
    #    e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div/div[1]")
    #    if e:
    #        s=e.text
    #        if s.find("Earnings are not available for") != -1:
    #            print("No data for %s: %s, skipping" %(stk.bscs.symbol, stk.bscs.name))
    #            return
    #except Exception as e:
    #    print(str(e))

    #try:
    #    e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[1]/div/div[1]/div/div/div/div[2]/div/p[1]")
    #    if e:
    #        print("Page does not exist for %s: %s, skipping" %(stk.bscs.symbol, stk.bscs.name))
    #        return
    #except Exception as e:
    #    print(str(e))


    #sign on popup
    #e = br.find_element_by_xpath("/html/body/div[9]/div/div/div[1]/div/i")
    #e.click()

    # date
    #e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[1]/div[4]/span[2]")
    #date=timestring.Date(e.text)
    #date=date.date
    #date=str(date.date())
    #earnings.date=date
    ##earnings.date=str(dt.now().date())

    ###high target
    ##e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[1]/div[1]/span")
    ##earnings.high_target = str_to_float(e.text)
    ##
    ###mean target
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[1]/div[2]/span")
    ##earnings.mean_target = str_to_float(e.text)
    ###low target
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[1]/div[3]/span")
    ##earnings.low_target=str_to_float(e.text)
    ###52 week high
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[2]/div[1]/span")
    ##earnings.fiftytwoweek_high=str_to_float(e.text)
    ###52 week low
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[2]/div[2]/span")
    ##earnings.fiftytwoweek_low=str_to_float(e.text)


    ###Earnings History
    ##for i in range(2,6):
    ##    #quarter dates
    ##    xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[1]/div/div[2]/div/div/ng-transclude/table/thead/tr/th[%d]/span[2]" %(i)
    ##    e = br.find_element_by_xpath(xpath)
    ##    earnings.hist.quarters.append(e.text)
    ##    #reported
    ##    xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[1]/div/div[2]/div/div/ng-transclude/table/tbody/tr[1]/td[%d]" %(i)
    ##    e = br.find_element_by_xpath(xpath)
    ##    rep = str_to_float(e.text)
    ##    earnings.hist.reported.append(rep)
    ##    #estimate
    ##    xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[1]/div/div[2]/div/div/ng-transclude/table/tbody/tr[2]/td[%d]" %(i)
    ##    e = br.find_element_by_xpath(xpath)
    ##    est = str_to_float(e.text)
    ##    earnings.hist.estimate.append(est)
    ##    #difference
    ##    earnings.hist.difference.append(round(rep - est,2))
    ##    #surprise
    ##    try:
    ##        earnings.hist.surprise.append(round(((rep - est)/ est), 3))
    ##    except ZeroDivisionError:
    ##        earnings.hist.surprise.append(0)

    #Earnings Estimates
    ##for i in range(2,6):
    ##    if i < 4:
    ##        #quarter dates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/thead/tr/th[%d]/span[2]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.quarters.append(e.text)

    ##        #average estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[1]/td[%i]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_avg_est.append(str_to_float(e.text))
    ##
    ##        #number of estimates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[2]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_num_est.append(str_to_float(e.text))
    ## 
    ##        #high estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[3]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_high_est.append(str_to_float(e.text))
    ##
    ##        #low estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[4]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_low_est.append(str_to_float(e.text))
    ##
    ##        #prior year
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[5]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_prior_yr.append(str_to_float(e.text))
    ##
    ##        #growth rate estimate (yoy)
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[6]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_gr_rate.append(round(str_to_float(e.text)/100, 3))

    ##    else:
    ##        #year dates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/thead/tr/th[%d]/span[2]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.years.append(e.text)

    ##        #average estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[1]/td[%i]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_avg_est.append(str_to_float(e.text))
    ##
    ##        #number of estimates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[2]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_num_est.append(str_to_float(e.text))
    ## 
    ##        #high estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[3]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_high_est.append(str_to_float(e.text))
    ##
    ##        #low estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[4]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_low_est.append(str_to_float(e.text))
    ##
    ##        #prior year
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[5]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_prior_yr.append(str_to_float(e.text))
    ##
    ##        #growth rate estimate (yoy)
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[6]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_gr_rate.append(round(str_to_float(e.text)/100, 3))

    #print(earnings.date)
    #print(earnings.high_target)
    #print(earnings.mean_target)
    #print(earnings.low_target)

    #print("Historical data")
    #print("Quarters: %r" %(earnings.hist.quarters))
    #print("Reported: %r" %(earnings.hist.reported))
    #print("Estimate: %r" %(earnings.hist.estimate))
    #print("Difference: %r" %(earnings.hist.difference))
    #print("Surprise: %r" %(earnings.hist.surprise))

    #print("Estimates")
    #print("Quarters: %r" %(earnings.est.quarters))
    #print("Years: %r" %(earnings.est.years))
    #
    #print("Quarter Avg Est: %r" %(earnings.est.q_avg_est))
    #print("Quarter Num Est: %r" %(earnings.est.q_num_est))
    #print("Quarter High Est: %r" %(earnings.est.q_high_est))
    #print("Quarter Low Est: %r" %(earnings.est.q_low_est))
    #print("Quarter Prior Yr: %r" %(earnings.est.q_prior_yr))
    #print("Quarter Growth Rate: %r" %(earnings.est.q_gr_rate))

    #print("Year Avg Est: %r" %(earnings.est.y_avg_est))
    #print("Year Num Est: %r" %(earnings.est.y_num_est))
    #print("Year High Est: %r" %(earnings.est.y_high_est))
    #print("Year Low Est: %r" %(earnings.est.y_low_est))
    #print("Year Prior Yr: %r" %(earnings.est.y_prior_yr))
    #print("Year Growth Rate: %r" %(earnings.est.y_gr_rate))

    update_DB_US_earnings_estimates(stk, earnings, fiftytwoweek_high, fiftytwoweek_low)

    #get_US_earnings_chart(earnings, br)
    close_browser(br)


def get_val(br, description, convert):
    soup = BeautifulSoup(br.page_source, 'html.parser')
    f=open("/home/vpetla/avgo-chart.html","w")
    f.write(soup.prettify())
    f.close()
    e = soup.find("td", {"class": "field-value"})
    try:
        print("%s: %s" % (description, e.text))
        if convert:
            return float(e.text)
        return e.text
        # print("%d: %s: %s" %(i, description, eps))
        # if i > 10:
        #    break
    except Exception as e:
        return 10000

def get_price(description):
    return round(float(description.split(",")[-1][:-1]), 2)

def get_date(br, description):
    soup = BeautifulSoup(br.page_source, 'html.parser')
    e = soup.find("td", {"class": "field-value"})
    e = e.find_next("td", {"class": "field-value"})
    #return e.text
    try:
        date = dt.strptime(e.text, '%m/%d/%Y').date()
    except Exception:
        PRINT_ERR(e.text)
        exit()
    return date
    #eps_date = description.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
    #eps_date = dt.strptime(eps_date, '%b %d %Y').date()
    #return str(eps_date)

perform_i=0
def perform(h):
    global perform_i
    try:
        perform_i +=1
        h.perform()
    except Exception as e:
        if perform_i > 0:
            print("h.perform() error")
            print(str(e))
            #exit()
            return False
        perform(h)
    return True

def scroll(br, direction):
    e=br.find_element_by_tag_name('html')
    for i in range(5):
        e.send_keys(direction)

def tab(br):
    print("tab")
    a = ac(br)
    a.send_keys(Keys.TAB).perform()

def popout_chart(br):
    a = ac(br)

    #Interactive chart
    we=br.find_element_by_class_name("bc-interactive-chart__wrapper-chart-content")
    h=a.move_to_element(we)
    h.context_click().perform()
    #soup=BeautifulSoup(br.page_source,'html.parser')
    #pattern=re.compile(r'Popout Chart')
    #e=soup.find(text=pattern)

    scroll(br, Keys.ARROW_DOWN)
    # Popout Chart
    we=br.find_element_by_css_selector("li.bc-interactive-chart-context-menu__menu-list-item:nth-child(28)")
    h=a.move_to_element(we)
    h.click().perform()
    WebDriverWait(br, 20).until(EC.number_of_windows_to_be(2))
    handles=br.window_handles
    br.switch_to_window(handles[0])
    br.close()
    br.switch_to_window(handles[-1])

def get_eps_for_element(br, description, convert, entries, offset, field, we, trial):
    entry = {}
    j = 0
    if trial == 1:
        a=ac(br)
        h = a.move_to_element(we)
        h.perform()
        time.sleep(0.1)
    while j in range(10):
        a = ac(br)
        val = get_val(br, description, convert)
        if field == "split_factor":
            pattern=re.compile(r'\d{1,4}-\d{1,4}')
            #pattern=re.compile(r'^[1-9]*-[1-9]*')
            if pattern.match(val):
                split = round(float(val.split("-")[0])/float(val.split("-")[-1]), 3)
                entry[get_date(br, description)] = {"price":get_price(description), "split":val, field:split}
                entries.update(entry)
                return j
        elif val != 10000:
            entry[get_date(br,description)] = {"price":get_price(description), field:val}
            entries.update(entry)
            #print(entries)
            return j
        if trial:
            #print("height: %d" %(we.size['height']))
            #print("width: %d" %(we.size['width']))
            x_offset = we.size['height'] / 4 #+ j
            y_offset  = we.size['width'] / 4 #+ j
            #h = a.move_to_element_with_offset(we, x_offset, y_offset)
            h = a.move_by_offset(offset, offset)
            time.sleep(1)
        else:
            h = a.move_by_offset(offset, offset)
        perform(h)
        time.sleep(1)
        j += 1
    return j

def convert_date(label):
    label = label.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
    return dt.strptime(label, '%B %Y').date()

def get_all_entries(br, stk, item, field, pattern, convert):
    entries = {}
    entry = {}

    time.sleep(2)
    scroll(br, Keys.ARROW_DOWN)
    soup = BeautifulSoup(br.page_source, 'html.parser')
    tags = soup.find({"g"}, {"class":"highcharts-series-group"})
    labels = tags.findAll({"rect"})
    start  = convert_date(str(labels[0].attrs['aria-label']))
    end    = convert_date(str(labels[-1].attrs['aria-label']))

    st = start
    db = DB.open_db('Stocks')
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "bscs.since", str(start))

    now = dt.now().date()
    while True:
        en = st + timedelta(days=365*10)
        if en >= now:
            en = now

        print("Selecting date")
        print("start: %s, end: %s" %(st, en))
        we = br.find_element_by_css_selector(".bc-glyph-calendar")
        we.click()
        d="%s/%s/%s"%(st.strftime('%m'), st.strftime('%d'), st.strftime('%Y'))
        we = br.find_element_by_xpath("/html/body/div[6]/div/div/form/div[3]/div[1]/div/input")
        we.clear()
        we.click()
        we.send_keys(d)
        time.sleep(0.5)
        we.send_keys(Keys.TAB)
        d="%s/%s/%s"%(en.strftime('%m'), en.strftime('%d'), en.strftime('%Y'))
        we = br.find_element_by_xpath("/html/body/div[6]/div/div/form/div[3]/div[2]/div/input")
        we.clear()
        we.click()
        we.send_keys(d)
        time.sleep(0.5)
        we.send_keys(Keys.TAB)
        #tab(br)
        #h=a.send_keys(d)
        #h.perform()
        br.find_element_by_css_selector("button.bc-button:nth-child(2)").click()
        time.sleep(2)
    
        soup = BeautifulSoup(br.page_source, 'html.parser')
        elements = soup.findAll(text=pattern)
    
        a = ac(br)
        i = 0
        print("elements: %d" % (len(elements)))
        if len(elements) > 0:
            #description = elements[0].parent.parent.attrs['aria-label']
            #d1date = description.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
            #d1date = dt.strptime(d1date, '%b %d %Y').date()
    
            #description = elements[-1].parent.parent.attrs['aria-label']
            #d2date = description.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
            #d2date = dt.strptime(d2date, '%b %d %Y').date()
            ##d1date = datetime.strptime(d1, '%m/%d/%Y')
            ##d2date = datetime.strptime(d2, '%m/%d/%Y')
            #print(d1date)
            #print(d2date)
            #if d1date > d2date:
            #    elements.reverse()
            #f = open("/home/vpetla/aapl-chart1.html","w")
            #f.write(soup.prettify())
            #f.close()
            #input("Press any key to continue")

            for e in elements:
                if i >= 0:
                    #print(e.parent.parent)
                    #if not 'fill' in e.parent.parent.attrs:
                    #    continue
                    description = e.parent.parent.attrs['aria-label']
                    #print(description)
                    #print(e.parent.parent)
                    attr = "g[aria-label=\'%s\'" % (description)
                    we = br.find_element(By.CSS_SELECTOR, attr)
                    a=ac(br)
                    h = a.move_to_element(we)
                    # h = a.move_to_element_with_offset(we,0,0)
                    if perform(h) is False:
                        print("Skipping %s" %(description))
                        continue
                    time.sleep(0.5)
                    offset = -1
                    j = get_eps_for_element(br, description, convert, entries, offset, field, we, 0)
                    if j == 20:
                        PRINT_ERR("%s: Couldn't get Value for : %r, checking the other way" %(stk.bscs.symbol, description))
                        offset = 1
                        a=ac(br)
                        h = a.move_to_element(we)
                        h.perform()
                        j = get_eps_for_element(br, description, convert, entries, offset, field, we, 1)
                        if j == 20:
                            PRINT_ERR("%s: Couldn't get Value for : %r" %(stk.bscs.symbol, description))
                            #entry = {}
                            #if field == "split_factor":
                            #    entry[get_date(br, description)] = {"price":get_price(description), "split":"100000:100000", field:100000}
                            #else:
                            #    entry[get_date(br,description)] = {"price":get_price(description), field:100000}
                            #entries.update(entry)
                            exit()
                        #e={}
                        #return e
                i += 1
        st = en
        if en >= now:
            break
        if en >= end:
            break

    pp = pprint.PrettyPrinter(indent=4)
    sorted_entries = {}
    for e in sorted(entries.keys()):
        sorted_entries[str(e)] = entries[e]
    #pp.pprint(sorted_entries)
    scroll(br, Keys.ARROW_UP)
    return sorted_entries

def thread_close_popups(br, lock):
    while True:
        e = None
        try:
            e = br.find_element_by_xpath("/html/body/div[8]/div[2]/div[1]")
        except Exception:
            pass
        if e:
            lock.acquire()
            try:
                e.click()
            finally:
                lock.release()
        time.sleep(1)

def close_login(br):
    try:
        br.switch_to_window(handles[-1])
        br.close()
        br.switch_to_window(handles[0])
    except:
        pass

def click(e):
    try:
        e.click()
    except ElementClickInterceptedException:
        close_login(br)

def find_element_by_css_selector(br, select):
    try:
        return br.find_element_by_css_selector(select)
    except Exception as e:
        print(str(e))
        soup=BeautifulSoup(br.page_source,"html.parser")
        f=open("/home/vpetla/stock-chart.html","w")
        f.write(soup.prettify())
        f.close()
        exit()

def toggle_earnings_button(br):
    # goto settings
    e = find_element_by_css_selector(br, "span.show-for-medium-up")
    click(e)
    # goto adjustments
    e = find_element_by_css_selector(br, "div.bc-tabs__tab:nth-child(3)")
    click(e)

    # select earnings
    e = find_element_by_css_selector(br,
        ".row-events > ul:nth-child(2) > li:nth-child(2) > div:nth-child(1) > label:nth-child(2)")
    click(e)

    # apply
    e = find_element_by_css_selector(br, "button.bc-button:nth-child(2)")
    click(e)

def toggle_dividend_button(br):
    # goto settings
    e = find_element_by_css_selector(br, "span.show-for-medium-up")
    click(e)

    # goto adjustments
    e = find_element_by_css_selector(br, "div.bc-tabs__tab:nth-child(3)")
    click(e)

    # select dividend
    e = find_element_by_css_selector(br,
        ".row-events > ul:nth-child(2) > li:nth-child(1) > div:nth-child(1) > label:nth-child(2)")
    click(e)

    # apply
    e = find_element_by_css_selector(br, "button.bc-button:nth-child(2)")
    click(e)

def toggle_split_button(br):
    # goto settings
    e = find_element_by_css_selector(br, "span.show-for-medium-up")
    click(e)

    # goto adjustments
    e = find_element_by_css_selector(br, "div.bc-tabs__tab:nth-child(3)")
    click(e)

    # select split
    e = find_element_by_css_selector(br,
        ".row-events > ul:nth-child(2) > li:nth-child(3) > div:nth-child(1) > label:nth-child(2)")
    click(e)

    # apply
    e = find_element_by_css_selector(br, "button.bc-button:nth-child(2)")
    click(e)

def set_max_range(br):
    try:
        # set 10 year range
        # e = br.find_element_by_css_selector("div.quick-settings:nth-child(2) > ul:nth-child(1) > li:nth-child(11)")
        # set MAX range
        e = br.find_element_by_css_selector("div.quick-settings:nth-child(2) > ul:nth-child(1) > li:nth-child(13)")
        e.click()
    except Exception as e:
        print(str(e))
        stk_file="/home/vpetla/%s-chart.html" %(stk.bscs.symbol)
        soup=BeautifulSoup(br.page_source,"html.parser")
        f=open(stk_file,"w")
        f.write(soup.prettify())
        f.close()
        exit()


def populate_US_EPS(stk):
    url = "https://www.barchart.com/stocks/quotes/%s/interactive-chart" %(stk.bscs.symbol)
    br = open_browser()

    #t1 = threading.Thread(target=close_popups, args=(br,lock,))
    #t1.start()

    try:
        br.get(url)
    except Exception:
        print("%s: %s webpage loading timeout, trying again" %(stk.bscs.symbol, stk.bscs.name))
        close_browser(br)
        time.sleep(5)
        br = open_browser()
        br.get(url)

    try:
        # e=br.find_element_by_xpath("//*[@id="ic_guyoff6702"]")
        e = br.find_element_by_xpath("/html/body/div[9]/div[2]/div[3]/div/img")
        if e:
            e.click()
    except Exception as e:
        pass
        #print(str(e))

    # try:
    #    e=br.find_element_by_xpath("//*[@id="off7131"]")
    #    if e:
    #        e.click()

    # set 10 year range
    #e = br.find_element_by_css_selector("div.quick-settings:nth-child(2) > ul:nth-child(1) > li:nth-child(11)")
    time.sleep(1)
    
    set_max_range(br)

    br.maximize_window()
    popout_chart(br)
    br.maximize_window()
    opts = WebDriverWait(br, 20).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.highcharts-background')))
    print("chart loaded")
    time.sleep(4)

    toggle_earnings_button(br)
    pattern = re.compile(r'^E$')
    eps_hist = get_all_entries(br, stk, "EPS_History", "eps", pattern, 1)
    toggle_earnings_button(br)

    time.sleep(1)
    set_max_range(br)
    time.sleep(3)
    toggle_dividend_button(br)
    pattern = re.compile(r'^D$')
    dividend_hist = get_all_entries(br, stk, "DIVIDEND_History", "dividend", pattern, 1)
    toggle_dividend_button(br)

    time.sleep(1)
    set_max_range(br)
    time.sleep(3)
    toggle_split_button(br)
    pattern = re.compile(r'^S$')
    split_hist = get_all_entries(br, stk, "SPLIT_History", "split_factor", pattern, 0)

    db = DB.open_db('Stocks')
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "fig.EPS_History", eps_hist)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "fig.DIVIDEND_History", dividend_hist)
    DB.update_field(db.US_Stocks, stk.bscs.symbol, "fig.SPLIT_History", split_hist)


    close_browser(br)
    gc.collect()
    #t1.join()

def get_US_quarterly_stock_page(symbol, name):
    path = "/mnt/usb/stockanalysis/US_Stocks/html_pages/%s" %(name)
    path = path.lstrip().rstrip().replace(",","")
    try:
        os.makedirs(path, exist_ok=True)
    except FileExistsError:
        PRINT_ERR("%s exists" %(symbol))
        return

    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=1" %(symbol)
    html_file = "%s/%s_income_quarterly_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=2" %(symbol)
    html_file = "%s/%s_income_quarterly_2.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=3" %(symbol)
    html_file = "%s/%s_income_quarterly_3.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=4" %(symbol)
    html_file = "%s/%s_income_quarterly_4.html" %(path, symbol)
    get_page(url, html_file)

    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=1" %(symbol)
    html_file = "%s/%s_cash_flow_quarterly_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=2" %(symbol)
    html_file = "%s/%s_cash_flow_quarterly_2.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=3" %(symbol)
    html_file = "%s/%s_cash_flow_quarterly_3.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=4" %(symbol)
    html_file = "%s/%s_cash_flow_quarterly_4.html" %(path, symbol)
    get_page(url, html_file)

    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=1" %(symbol)
    html_file = "%s/%s_balance_sheet_quarterly_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=2" %(symbol)
    html_file = "%s/%s_balance_sheet_quarterly_2.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=3" %(symbol)
    html_file = "%s/%s_balance_sheet_quarterly_3.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=4" %(symbol)
    html_file = "%s/%s_balance_sheet_quarterly_4.html" %(path, symbol)
    get_page(url, html_file)

    return path
 
def get_US_stock_page(symbol, name):
    path = "/mnt/usb/stockanalysis/US_Stocks/html_pages/%s" %(name)
    path = path.lstrip().rstrip().replace(",","")
    try:
        os.makedirs(path, exist_ok=True)
    except FileExistsError:
        PRINT_ERR("%s exists" %(symbol))
        return

    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/annual?reportPage=1" %(symbol)
    html_file = "%s/%s_income_annual_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/annual?reportPage=2" %(symbol)
    html_file = "%s/%s_income_annual_2.html" %(path, symbol)
    get_page(url, html_file)

    #url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=1" %(symbol)
    #html_file = "%s/%s_income_quarterly_1.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=2" %(symbol)
    #html_file = "%s/%s_income_quarterly_2.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=3" %(symbol)
    #html_file = "%s/%s_income_quarterly_3.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/income-statement/quarterly?reportPage=4" %(symbol)
    #html_file = "%s/%s_income_quarterly_4.html" %(path, symbol)
    #get_page(url, html_file)
 
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/annual?reportPage=1" %(symbol)
    html_file = "%s/%s_cash_flow_annual_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/annual?reportPage=2" %(symbol)
    html_file = "%s/%s_cash_flow_annual_2.html" %(path, symbol)
    get_page(url, html_file)

    #url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=1" %(symbol)
    #html_file = "%s/%s_cash_flow_quarterly_1.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=2" %(symbol)
    #html_file = "%s/%s_cash_flow_quarterly_2.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=3" %(symbol)
    #html_file = "%s/%s_cash_flow_quarterly_3.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/quarterly?reportPage=4" %(symbol)
    #html_file = "%s/%s_cash_flow_quarterly_4.html" %(path, symbol)
    #get_page(url, html_file)

    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/annual?reportPage=1" %(symbol)
    html_file = "%s/%s_balance_sheet_annual_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/annual?reportPage=2" %(symbol)
    html_file = "%s/%s_balance_sheet_annual_2.html" %(path, symbol)
    get_page(url, html_file)

    #url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=1" %(symbol)
    #html_file = "%s/%s_balance_sheet_quarterly_1.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=2" %(symbol)
    #html_file = "%s/%s_balance_sheet_quarterly_2.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=3" %(symbol)
    #html_file = "%s/%s_balance_sheet_quarterly_3.html" %(path, symbol)
    #get_page(url, html_file)
    #url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/quarterly?reportPage=4" %(symbol)
    #html_file = "%s/%s_balance_sheet_quarterly_4.html" %(path, symbol)
    #get_page(url, html_file)

    url = "https://www.barchart.com/stocks/quotes/%s/profile" %(symbol)
    html_file = "%s/%s_profile.html" %(path, symbol)
    get_page(url, html_file)

    return path

def get_all_US_html_pages():
    db = open_db('Stocks')
    docs = db.US_Stocks_List.find({})
    for i, doc in enumerate(docs):
        if i > -1:
            sym  = doc['symbol']
            name = doc['Name']
            if "&#39;" in name:
                print("stk has &")
                name = name.replace("&#39;", "\'")
                db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}})
            if "/" in name:
                print("stk has /")
                name = name.replace("/", "")
                db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}}) 
            if "^" in sym:
                print("symbol has ^")
                sym = sym.replace("^", "-")
                print(sym)
                db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"symbol": sym}})

            print("%d: %s: %s "%(i, sym, name))
            get_US_stock_page(sym, name)

def get_html(stock_page):
    try:
        html = open(stock_page)
    except FileNotFoundError:
        PRINT_ERR("Failed to open %s" %(stock_page))
        return None
    return html

def get_India_stock_page(stock):
    driver = webdriver.Firefox()
    driver.get("http://www.ratestar.in/home")
    old_url = driver.current_url
    elem = driver.find_element_by_name("txtStock")

    elem.clear()
    for i in range(len(stock)):
        elem.send_keys(str(stock[i]))
        time.sleep(10/1000)
        #divs = driver.find_element_by_xpath()
        #s = Select(elem)
        #driver.find_element_by_css_selector("button.btn.btn-default").click()
        opts = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.ID, 'listPlacementStock')))
        time.sleep(1)
        PRINT_DBG("Opts: %r : %r" %(len(opts.text), opts.text))

        #if len(items) == 1:
        if len(opts.text) == 0:
            PRINT("Unable to parse %r" % (stock))
            f = open("unparsed_stocks3.txt", "a")
            f.write(stock)
            f.write("\n")
            f.close()
            driver.close()
            return
        if not '\n' in opts.text:
            stock_name = opts.text
            #time.sleep(5)
            elem.send_keys(Keys.RETURN)
            break

        #attr=driver.find_element_by_name('txtStock').get_attribute('innerHTML')
        #attr=elem.get_attribute('innerHTML')
    #elem.send_keys(stock, Keys.ARROW_DOWN)
    #time.sleep(2)
    #elem.send_keys(Keys.RETURN)
    
    #time.sleep(20)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.ID, 'lblCompany')))
    except TimeoutException:
        PRINT("Unable to parse %r" %(stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
        return
    #PRINT_DBG(str(html_src))

    if driver.current_url == old_url:
        PRINT("Unable to parse %r" %(stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        #PRINT_DBG("Found stock %r" %(stock))
        html_src=driver.page_source
        html_file = "html_pages/%s.html" %(stock_name)
        f = open(html_file, "w")
        f.write(html_src)
        f.close()
 
#    try:
#        element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
#        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, 'IdOfMyElement')))
#        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
#        html_file = "html_pages/%s.html" %(stock)  
#        f = open(html_file, "w")
#        f.write(html_src)
#        f.close()
#    finally:
#        PRINT_DBG("Unable to parse %r" %(stock))
#        f = open("unparsed_stocks.txt", "a")
#        f.write(stock)
#        f.write("\n")
#        f.close()

    driver.close()
    
    #try:
    #    element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
    #finally:
    #    driver.close()
    
    #assert "No results found." not in driver.page_source
    #time.sleep(5)

def get_India_all_stocks_html():
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
#    with open("missing_files.txt") as f:
#        for line in f:
#            line = line.replace("\n","")
#            print(line)
#            get_stock_page(line)

    for i in range(0,sheet.nrows):
    #for i in range(1,10):
        PRINT("%r: %r" %(i, sheet.cell_value(i, 2)))
        get_India_stock_page(sheet.cell_value(i,2))
        
#    f = open('NSE_Stocks.csv')
#    #f = open('BSE_Stocks.csv')
#    csv_f = csv.reader(f)
#    for row in csv_f:
#        PRINT_DBG(row)
#        #PRINT_DBG(row[1])
#        #PRINT_DBG(row[0], row[1], row[2],)

# Get stock split information
def get_stock_split_info_yahoo(stk):
    sym = stk.bscs.symbol + '.BO'
    #get split info from Yahoo Finance
    data = yf(sym).get_key_statistics_data()
    stk.bscs.split_factor = float(Fraction(data[sym]['lastSplitFactor']))
    d = data[sym]['lastSplitDate']
    stk.bscs.split_date = d
    stk.bscs.split_year = datetime.datetime.strptime(d, '%Y-%m-%d').year 

def get_stock_split_info(stk):
    wb = xlrd.open_workbook('India_Stocks/split_data.xls')
    sheet = wb.sheet_by_index(0)
    for i in range(1,sheet.nrows):
        if str(sheet.cell_value(i, 0)) == stk.bscs.name:
            stk.bscs.split_date = sheet.cell_value(i,1)
            stk.bscs.split_year = datetime.datetime.strptime(stk.bscs.split_date, '%d-%b-%Y').year
            try:
                stk.bscs.split_factor = int(sheet.cell_value(i, 3)) / int(sheet.cell_value(i,4))
            except ZeroDivisionError:
                stk.bscs.split_factor=1
            return
    if stk.bscs.face_value != 10:
        PRINT_ERR("Could not find split date for %s, facevalue: %r" %(stk.bscs.symbol, stk.bscs.face_value))   

# Get symbol name for bse symbol
# Get sector information
def get_symbol_and_sector(stk):
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    #sheet.cell_value(0,0)

    for i in range(1,sheet.nrows):
        if str(int(sheet.cell_value(i, 0))) == stk.bscs.bse_symbol:
            stk.bscs.symbol = sheet.cell_value(i,1)
            stk.bscs.sector = sheet.cell_value(i,7)
            return
    PRINT_ERR("Cant find symbol name for %s" %(stk.bscs.bse_symbol))


