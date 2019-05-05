import DB
import common

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

# Parsing HTML
import requests 

#Yahoo Financials
from yahoofinancials import YahooFinancials as yf

import pandas_datareader as pdr
import pandas_datareader.data as data

from datetime import datetime as dt
import datetime

# Excel operations
#import csv
import xlrd

# Date
import datetime
from datetime import date

#List Files
from fractions import Fraction

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
    stk.bscs.shares_outstanding = d.sharesOutstanding.to_list()[0]
    return stk

def get_price_growth(country, stk, years, data_type):
    yrs = years
    if data_type == 'HOT':
        end = dt.today()
        st = dt(end.year-years, end.month, end.day)
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
        del data
        if years == 5:
            stk.bscs.hist_price_5 = st_price
        else:
            end = dt.today()
            st = dt(end.year-5, end.month, end.day)
            data = pdr.DataReader(stk.bscs.symbol, 'yahoo', st, end)
            stk.bscs.hist_price_5 = data.iat[0, data.columns.get_loc('Close')]
            del data
 
        if years == 10:
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
    growth = round(((en_price/st_price)**(1/years)-1), 2)
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
    if country == 'India':
        sym = sym + '.BO'
    elif country != 'US':
        PRINT_ERR("Unknown Country")
        return 0
    return yf(sym).get_current_price()

def get_page(url, html_file):
    html=requests.get(url)
    if html.status_code == 200:
        common.write_to_file(html.text, html_file)
    else:
        PRINT_ERR("Couldnt get page : %s" %(url))

def get_US_stock_page(symbol, name):
    path = "./US_Stocks/html_pages/%s" %(name)
    try:
        os.makedirs(path, exist_ok=True)
    except FileExistsError:
        PRINT_ERR("%s exists" %(symbol))
        return

    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/annual?reportPage=1" %(symbol)
    html_file = "%s/%s_income_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/income-statement/annual?reportPage=2" %(symbol)
    html_file = "%s/%s_income_2.html" %(path, symbol)
    get_page(url, html_file)
   
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/annual?reportPage=1" %(symbol)
    html_file = "%s/%s_cash_flow_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/cash-flow/annual?reportPage=2" %(symbol)
    html_file = "%s/%s_cashflow_2.html" %(path, symbol)
    get_page(url, html_file)

    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/annual?reportPage=1" %(symbol)
    html_file = "%s/%s_balance_sheet_1.html" %(path, symbol)
    get_page(url, html_file)
    url = "https://www.barchart.com/stocks/quotes/%s/balance-sheet/annual?reportPage=2" %(symbol)
    html_file = "%s/%s_balance_sheet_2.html" %(path, symbol)
    get_page(url, html_file)

    url = "https://www.barchart.com/stocks/quotes/%s/profile" %(symbol)
    html_file = "%s/%s_profile.html" %(path, symbol)
    get_page(url, html_file)

    return name

def get_all_US_html_pages():
    db = open_db('Stocks')
    docs = db.US_Stocks_List.find({})
    for i, doc in enumerate(docs):
        if i > 3030:
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


