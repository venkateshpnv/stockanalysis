import DB
from common import *

import os
import time
#Web Driver
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.support.ui import Select
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

import excel
import conf

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
            if sno > 0:
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
    except pdr._utils.RemoteDataError:
        PRINT_ERR("Unable to get data for %s: %s"%(stk.bscs.name, stk.bscs.symbol))
        return None
    # Add moving average etc. Refer /tmp/test.csv for details
    stk.bscs.volume = (d.averageDailyVolume3Month.to_list()[0])
    #stk.bscs.volume = d.regularMarketVolume.to_list()[0]
    stk.bscs.mcap   = float(d.marketCap.to_list()[0])/1000000
    stk.bscs.price  = (d.price.to_list()[0])
    stk.bscs.outstanding_shares = d.sharesOutstanding.to_list()[0]
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


